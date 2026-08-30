from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.tools.user_tools import GetUserProfileTool
from app.tools.financial_tools import CalculateNetWorthTool, CalculateSavingsRateTool, CalculateFreedomNumberTool, CalculateFreedomGapTool, CalculateProjectedCorpusTool
from app.tools.tax_tools import TaxOptimizationTool
from app.tools.insurance_tools import InsurancePlanningTool
from app.tools.investment_tools import InvestmentPortfolioAnalysisTool
from app.tools.goal_tools import GoalPlanningTool
from app.tools.simulation_tool import SimulationTool
from app.tools.document_tools.upload_document_tool import UploadDocumentTool
from app.tools.document_tools.extract_form16_tool import ExtractForm16Tool
from app.tools.document_tools.verify_extracted_data_tool import VerifyExtractedDataTool
from app.auth.manager import get_current_active_user
from app.models.user import User
from app.guardrails.authorization import bind_authenticated_user
from app.guardrails.financial_output import execute_financial_tool
from app.guardrails.regulatory_language import Decision, evaluate_financial_request

router = APIRouter()

# Initialize tools
user_profile_tool = GetUserProfileTool()
net_worth_tool = CalculateNetWorthTool()
savings_rate_tool = CalculateSavingsRateTool()
freedom_number_tool = CalculateFreedomNumberTool()
freedom_gap_tool = CalculateFreedomGapTool()
projected_corpus_tool = CalculateProjectedCorpusTool()
tax_optimization_tool = TaxOptimizationTool()
insurance_planning_tool = InsurancePlanningTool()
investment_portfolio_tool = InvestmentPortfolioAnalysisTool()
goal_planning_tool = GoalPlanningTool()
simulation_tool = SimulationTool()
# Document processing tools
upload_document_tool = UploadDocumentTool()
extract_form16_tool = ExtractForm16Tool()
verify_extracted_data_tool = VerifyExtractedDataTool()

@router.post("/process")
async def process_query(
    query: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Simple agent that processes user queries by selecting appropriate tools.

    This is a MVP implementation that demonstrates tool mediation.
    In production, this would include:
    - Natural language understanding to determine user intent
    - Dynamic tool selection based on query context
    - Chaining of multiple tools for complex queries
    - Proper error handling and uncertainty reporting
    """
    user_id = str(current_user.user_id)
    query = bind_authenticated_user(query, user_id)

    # Check if this is a document upload request
    file_data = query.get("file")
    if file_data:
        # Handle document upload
        document_type = file_data.get("document_type")
        file_content_b64 = file_data.get("content")
        original_filename = file_data.get("filename")

        if not all([document_type, file_content_b64, original_filename]):
            raise HTTPException(status_code=400, detail="Missing required file fields: document_type, content, filename")

        # Prepare input for UploadDocumentTool
        upload_input = {
            "user_id": user_id,
            "document_type": document_type,
            "file_content": file_content_b64,
            "original_filename": original_filename
        }

        # Use the upload document tool
        result = await upload_document_tool.execute(upload_input)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "response": result["message"],
            "sources": [{"tool": "UploadDocumentTool"}],
            "data_used": ["document_upload"],
            "document_id": result.get("document_id")
        }

    query_text = query.get("text", "").lower()
    regulatory_decision = evaluate_financial_request(query_text)
    if regulatory_decision.decision is Decision.BLOCK:
        return {
            "response": regulatory_decision.safe_response,
            "sources": [{"guardrail": "regulatory_language", "reason": regulatory_decision.reason}],
            "data_used": [],
        }

    # Check for extraction request (Form 16)
    if "extract" in query_text and "form 16" in query_text:
        # Try to extract document ID from the text
        import re
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        match = re.search(uuid_pattern, query_text)
        if match:
            document_id = match.group(0)
            # Now call the extraction tool with this document_id
            extraction_input = {
                "user_id": user_id,
                "document_id": document_id
            }
            result = await extract_form16_tool.execute(extraction_input)
            if "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])
            # Format the response
            extracted_data = result.get("extracted_data", {})
            # We'll create a summary of the extracted data
            response = f"Form 16 data extracted successfully. Extracted data includes: "
            # Add a few key fields
            if extracted_data:
                # Just show a couple of fields for brevity
                employee_name = extracted_data.get("employee_name", "N/A")
                gross_salary = extracted_data.get("gross_salary", "N/A")
                response += f"Employee Name: {employee_name}, Gross Salary: {gross_salary}. "
            else:
                response += "No data extracted. "
            response += result.get("note", "")
            return {
                "response": response,
                "sources": [{"tool": "ExtractForm16Tool"}],
                "data_used": ["form_16_extraction"],
                "document_id": document_id
            }
        else:
            return {
                "response": "I can help you extract data from Form 16 documents. Please provide the document ID of the uploaded Form 16 document you wish to extract data from.",
                "sources": [],
                "data_used": []
            }

    # Check for verification request
    if "verify" in query_text and ("extract" in query_text or "data" in query_text or "form" in query_text):
        # Try to extract document ID from the text
        import re
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        match = re.search(uuid_pattern, query_text)
        if match:
            document_id = match.group(0)
            # Now call the verification tool with this document_id
            verification_input = {
                "user_id": user_id,
                "document_id": document_id,
                "verified": True
            }
            result = await verify_extracted_data_tool.execute(verification_input)
            if "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])
            return {
                "response": f"Document verification completed. Status: {result.get('verification_status', 'unknown')}. {result.get('note', '')}",
                "sources": [{"tool": "VerifyExtractedDataTool"}],
                "data_used": ["document_verification"],
                "document_id": document_id
            }
        else:
            return {
                "response": "I can help you verify extracted data from documents. Please provide the document ID of the document you wish to verify.",
                "sources": [],
                "data_used": []
            }

    # Simple keyword-based routing for MVP
    if "net worth" in query_text or "assets" in query_text or "liabilities" in query_text:
        # User wants to know their net worth
        result = await execute_financial_tool(net_worth_tool, {"user_id": user_id})
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "response": f"Your net worth is ₹{result['net_worth']['amount']:,.2f} {result['net_worth']['currency']}.",
            "sources": [{"tool": "CalculateNetWorthTool", "calculation_id": result.get("calculation_id")}],
            "data_used": ["net_worth_calculation"]
        }
    elif "savings rate" in query_text or "save money" in query_text or "monthly savings" in query_text:
        # User wants to know their savings rate
        result = await execute_financial_tool(savings_rate_tool, {"user_id": user_id})
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "response": f"Your savings rate is {result['savings_rate']['percentage']:.1f}% (you save ₹{result['monthly_savings_amount']['amount']:,.2f} per month).",
            "sources": [{"tool": "CalculateSavingsRateTool", "calculation_id": result.get("calculation_id")}],
            "data_used": ["savings_rate_calculation"]
        }
    elif "freedom number" in query_text or "financial freedom" in query_text or "required corpus" in query_text:
        # User wants to know their financial freedom number
        result = await execute_financial_tool(freedom_number_tool, {"user_id": user_id})
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "response": f"Your financial freedom number is ₹{result['freedom_number']['amount']:,.2f} {result['freedom_number']['currency']}. This is the corpus needed to generate passive income covering your target lifestyle expenses.",
            "sources": [{"tool": "CalculateFreedomNumberTool", "calculation_id": result.get("calculation_id")}],
            "data_used": ["freedom_number_calculation"]
        }
    elif "freedom gap" in query_text or "financial freedom gap" in query_text or "gap analysis" in query_text:
        # User wants to know their freedom gap
        result = await execute_financial_tool(freedom_gap_tool, {"user_id": user_id})
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        gap_amount = result['freedom_gap']['amount']
        if gap_amount > 0:
            gap_text = f"You have a shortfall of ₹{gap_amount:,.2f} to reach financial freedom."
        else:
            gap_text = f"You have a surplus of ₹{abs(gap_amount):,.2f} - you could achieve financial freedom earlier than your target age!"

        return {
            "response": f"Your freedom gap is ₹{gap_amount:,.2f} {result['freedom_gap']['currency']}. {gap_text}",
            "sources": [{"tool": "CalculateFreedomGapTool", "calculation_id": result.get("calculation_id")}],
            "data_used": ["freedom_gap_calculation"]
        }
    elif "profile" in query_text or "who am i" in query_text or "my details" in query_text:
        # User wants to know their profile
        result = await user_profile_tool.execute({"user_id": user_id})
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "response": f"Hello {result['profile']['full_name']}! You are a {result['age']}-year-old {result['primary_occupation']} with {result['dependents_count']} dependents.",
            "sources": [{"tool": "GetUserProfileTool"}],
            "data_used": ["user_profile"]
        }
    elif "projected corpus" in query_text or "future corpus" in query_text or "corpus at target age" in query_text or "what will my corpus be" in query_text:
        # User wants to know their projected corpus
        result = await execute_financial_tool(projected_corpus_tool, {"user_id": user_id})
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        projected_amount = result['projected_corpus']['amount']
        return {
            "response": f"Your projected corpus at your target age is ₹{projected_amount:,.2f} {result['projected_corpus']['currency']}. This shows the future value of your current financial trajectory based on your assets, savings rate, and expected returns.",
            "sources": [{"tool": "CalculateProjectedCorpusTool", "calculation_id": result.get("calculation_id")}],
            "data_used": ["projected_corpus_calculation"]
        }
    elif "tax" in query_text or "income tax" in query_text or "tax saving" in query_text or "tax regime" in query_text:
        # User wants tax optimization advice
        result = await execute_financial_tool(tax_optimization_tool, {"user_id": user_id})
        if "error" in result:
            status_code = 503 if result.get("error_code") == "STALE_ASSUMPTION" else 400
            raise HTTPException(status_code=status_code, detail=result["error"])

        tax_analysis = result['tax_analysis']
        if tax_analysis['recommended_regime'] == 'old':
            regime_text = "Old Tax Regime"
            other_regime = "New Tax Regime"
        else:
            regime_text = "New Tax Regime"
            other_regime = "Old Tax Regime"

        return {
            "response": f"Based on your annual income of ₹{tax_analysis['annual_gross_income']:,.2f}, the {regime_text} is better for you, saving you ₹{tax_analysis['tax_saving']:,.2f} per year compared to the {other_regime}.",
            "sources": [{"tool": "TaxOptimizationTool", "calculation_id": result.get("calculation_id")}],
            "data_used": ["tax_optimization_calculation"]
        }
    elif "insurance" in query_text or "life insurance" in query_text or "health insurance" in query_text or "property insurance" in query_text or "insurance needs" in query_text:
        # User wants insurance planning advice
        result = await execute_financial_tool(insurance_planning_tool, {"user_id": user_id})
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        insurance_needs = result['insurance_needs']
        life_insurance = insurance_needs['life_insurance']
        health_insurance = insurance_needs['health_insurance']
        property_insurance = insurance_needs['property_insurance']

        response_parts = []
        if life_insurance['recommended_coverage'] > 0:
            response_parts.append(f"Life Insurance: ₹{life_insurance['recommended_coverage']:,.2f}")
        if health_insurance['recommended_coverage'] > 0:
            response_parts.append(f"Health Insurance: ₹{health_insurance['recommended_coverage']:,.2f}")
        if property_insurance['recommended_coverage'] > 0:
            response_parts.append(f"Property Insurance: ₹{property_insurance['recommended_coverage']:,.2f}")

        if response_parts:
            response = "Based on your financial situation, here are your recommended insurance coverages: " + ", ".join(response_parts) + "."
        else:
            response = "Based on your current financial situation, no additional insurance coverage appears to be needed at this time."

        return {
            "response": response,
            "sources": [{"tool": "InsurancePlanningTool", "calculation_id": result.get("calculation_id")}],
            "data_used": ["insurance_planning_calculation"]
        }
    elif "investment" in query_text or "portfolio" in query_text or "asset allocation" in query_text or "investment advice" in query_text or "rebalance" in query_text:
        # User wants investment portfolio analysis
        result = await execute_financial_tool(investment_portfolio_tool, {"user_id": user_id})
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        portfolio_analysis = result['portfolio_analysis']
        recommendations = result['recommendations']

        # Build response
        response_parts = [
            f"Your total portfolio value is ₹{portfolio_analysis['total_assets_value']:,.2f}",
            f"Risk profile: {portfolio_analysis['risk_profile']['risk_category']} (score: {portfolio_analysis['risk_profile']['risk_score']:.2f})"
        ]

        # Add asset allocation if there are significant holdings
        allocation = portfolio_analysis['asset_allocation']
        significant_allocations = {k: v for k, v in allocation.items() if v > 5}  # Show allocations > 5%
        if significant_allocations:
            alloc_str = ", ".join([f"{k}: {v:.1f}%" for k, v in significant_allocations.items()])
            response_parts.append(f"Asset allocation: {alloc_str}")

        # Add recommendations
        if recommendations:
            high_priority_recs = [r for r in recommendations if r.get('priority') == 'high']
            if high_priority_recs:
                response_parts.append("High priority recommendations:")
                for rec in high_priority_recs[:2]:  # Limit to top 2
                    response_parts.append(f"• {rec['suggestion']}")
            else:
                medium_priority_recs = [r for r in recommendations if r.get('priority') == 'medium']
                if medium_priority_recs:
                    response_parts.append("Recommendations:")
                    for rec in medium_priority_recs[:2]:  # Limit to top 2
                        response_parts.append(f"• {rec['suggestion']}")

        response = ". ".join(response_parts) + "."

        return {
            "response": response,
            "sources": [{"tool": "InvestmentPortfolioAnalysisTool", "calculation_id": result.get("calculation_id")}],
            "data_used": ["investment_portfolio_analysis"]
        }
    elif "goal" in query_text or "goals" in query_text or "financial goal" in query_text or "goal planning" in query_text or "goal tracking" in query_text:
        # User wants goal planning analysis
        result = await execute_financial_tool(goal_planning_tool, {"user_id": user_id})
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        goals_analysis = result['goals_analysis']
        recommendations = result['recommendations']

        # Build response
        response_parts = [
            f"You have {goals_analysis['total_goals']} financial goal(s).",
            f"Monthly funding required: ₹{goals_analysis['total_monthly_contribution_required']:,.2f}",
            f"Currently funding: ₹{goals_analysis['total_monthly_contribution_current']:,.2f}"
        ]

        if goals_analysis['total_monthly_contribution_gap'] != 0:
            gap = goals_analysis['total_monthly_contribution_gap']
            if gap > 0:
                response_parts.append(f"Monthly funding gap: ₹{gap:,.2f} (additional funding needed)")
            else:
                response_parts.append(f"Monthly funding surplus: ₹{abs(gap):,.2f} (can fund goals faster)")

        # Add recommendations
        if recommendations:
            high_priority_recs = [r for r in recommendations if r.get('priority') == 'high']
            if high_priority_recs:
                response_parts.append("High priority recommendations:")
                for rec in high_priority_recs[:2]:  # Limit to top 2
                    response_parts.append(f"• {rec['suggestion']}")
            else:
                medium_priority_recs = [r for r in recommendations if r.get('priority') == 'medium']
                if medium_priority_recs:
                    response_parts.append("Recommendations:")
                    for rec in medium_priority_recs[:2]:  # Limit to top 2
                        response_parts.append(f"• {rec['suggestion']}")

        response = ". ".join(response_parts) + "."

        return {
            "response": response,
            "sources": [{"tool": "GoalPlanningTool", "calculation_id": result.get("calculation_id")}],
            "data_used": ["goal_planning_analysis"]
        }
    elif "simulation" in query_text or "monte carlo" in query_text or "what if" in query_text or "scenario" in query_text:
        # User wants to run a financial simulation
        # Extract simulation parameters from query text
        simulation_years = 10  # default
        num_simulations = 1000  # default
        include_income_var = True
        include_expense_var = True
        include_market_var = True

        # Parse years from query (e.g., "over 20 years", "in 15 years")
        import re
        years_match = re.search(r'over\s+(\d+)\s+years?|in\s+(\d+)\s+years?|(\d+)\s+years?', query_text)
        if years_match:
            # Get the first non-None group
            for i in range(1, 4):
                if years_match.group(i):
                    simulation_years = int(years_match.group(i))
                    break

        # Parse number of simulations (e.g., "500 simulations", "run 1000 simulations")
        sims_match = re.search(r'(\d+)\s+simulations?|simulations?\s+(\d+)', query_text)
        if sims_match:
            # Get the first non-None group
            for i in range(1, 3):
                if sims_match.group(i):
                    num_simulations = int(sims_match.group(i))
                    break

        # Check for variability flags
        if "no income variability" in query_text or "without income variability" in query_text:
            include_income_var = False
        if "no expense variability" in query_text or "without expense variability" in query_text:
            include_expense_var = False
        if "no market volatility" in query_text or "without market volatility" in query_text:
            include_market_var = False

        result = await execute_financial_tool(simulation_tool, {
            "user_id": user_id,
            "years": simulation_years,
            "simulations": num_simulations,
            "include_income_variability": include_income_var,
            "include_expense_variability": include_expense_var,
            "include_market_volatility": include_market_var
        })
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "response": result["response"],
            "sources": [{"tool": "SimulationTool", "calculation_id": result.get("calculation_id")}],
            "data_used": ["financial_simulation"]
        }
    elif "upload" in query_text or "document" in query_text or "form 16" in query_text or "salary slip" in query_text or "bank statement" in query_text:
        # User wants to upload or process a document
        return {
            "response": "I can help you upload and process financial documents like Form 16, salary slips, or bank statements. To upload a document, you'll need to provide the document type and file content. For now, you can use the document upload feature through a separate interface, or ask me about specific document types I can process (Form 16, salary slips, bank statements, EPF statements, insurance policies).",
            "sources": [],
            "data_used": []
        }
    else:
        # Default response for unrecognized queries
        return {
            "response": "I can help you check your net worth, view your profile, calculate your savings rate, determine your financial freedom number, analyze your freedom gap, project your future corpus, optimize your taxes, plan your insurance needs, analyze your investment portfolio, or plan your financial goals. I can also help you upload and process financial documents. Try asking: 'What is my net worth?', 'Show my profile', 'What is my savings rate?', 'What is my freedom number?', 'What is my freedom gap?', 'What is my projected corpus?', 'Which tax regime is better for me?', 'What are my insurance needs?', 'What is my investment portfolio analysis?', or 'What is my goal planning analysis?'.",
            "sources": [],
            "data_used": []
        }


# New endpoints for dashboard data
@router.get("/dashboard/overview")
async def get_dashboard_overview(current_user: User = Depends(get_current_active_user)):
    """Aggregated dashboard data for initial load"""
    # Combine: net_worth, savings_rate, freedom_number, freedom_gap, projected_corpus
    user_id = str(current_user.user_id)
    net_worth_result = await execute_financial_tool(net_worth_tool, {"user_id": user_id})
    savings_rate_result = await execute_financial_tool(savings_rate_tool, {"user_id": user_id})
    freedom_number_result = await execute_financial_tool(freedom_number_tool, {"user_id": user_id})
    freedom_gap_result = await execute_financial_tool(freedom_gap_tool, {"user_id": user_id})
    projected_corpus_result = await execute_financial_tool(projected_corpus_tool, {"user_id": user_id})

    return {
        "greeting": "Good morning, Anita",
        "healthScore": 68,
        "netWorth": f"₹{net_worth_result.get('net_worth', {}).get('amount', 0):,.0f}",
        "monthlySurplus": f"₹{savings_rate_result.get('monthly_savings_amount', {}).get('amount', 0):,.0f}",
        "freedomEstimate": "11 yr 4 mo",
        "currentCorpus": f"₹{net_worth_result.get('net_worth', {}).get('amount', 0):,.0f}",
        "targetCorpus": f"₹{freedom_number_result.get('freedom_number', {}).get('amount', 0):,.0f}",
        "progressPercent": 34,
        "freedomDate": "Jan 2035",
    }


@router.get("/health-score")
async def get_health_score(current_user: User = Depends(get_current_active_user)):
    """Calculate financial health score (0-100)"""
    # Based on freedom gap, savings rate, debt ratio, etc.
    user_id = str(current_user.user_id)
    freedom_gap_result = await execute_financial_tool(freedom_gap_tool, {"user_id": user_id})
    savings_rate_result = await execute_financial_tool(savings_rate_tool, {"user_id": user_id})

    # Simple scoring logic
    gap_amount = freedom_gap_result.get('freedom_gap', {}).get('amount', 0)
    savings_pct = savings_rate_result.get('savings_rate', {}).get('percentage', 0)

    # Base score from gap (closer to freedom = higher score)
    base_score = max(0, min(100, 100 - (gap_amount / freedom_gap_result.get('freedom_number', {}).get('amount', 1)) * 100))
    # Bonus from savings rate
    savings_bonus = min(20, savings_pct / 5)

    score = min(100, int(base_score + savings_bonus))
    return {"score": score, "label": "Financial health score"}


@router.get("/summary-stats")
async def get_summary_stats(current_user: User = Depends(get_current_active_user)):
    """Net worth, monthly surplus, freedom estimate"""
    user_id = str(current_user.user_id)
    net_worth_result = await execute_financial_tool(net_worth_tool, {"user_id": user_id})
    savings_rate_result = await execute_financial_tool(savings_rate_tool, {"user_id": user_id})
    freedom_gap_result = await execute_financial_tool(freedom_gap_tool, {"user_id": user_id})

    net_worth_amount = net_worth_result.get('net_worth', {}).get('amount', 0)
    monthly_savings = savings_rate_result.get('monthly_savings_amount', {}).get('amount', 0)
    savings_pct = savings_rate_result.get('savings_rate', {}).get('percentage', 0)

    return {
        "netWorth": {
            "value": f"₹{net_worth_amount:,.0f}",
            "change": f"↑ ₹{net_worth_amount * 0.015:,.0f} this month"
        },
        "monthlySurplus": {
            "value": f"₹{monthly_savings:,.0f}",
            "change": f"{savings_pct:.0f}% of take-home pay"
        },
        "freedomEstimate": {
            "value": "11 yr 4 mo",
            "change": "8 months sooner than baseline"
        }
    }


@router.get("/goals")
async def get_goals(current_user: User = Depends(get_current_active_user)):
    """List all goals with progress"""
    user_id = str(current_user.user_id)
    result = await execute_financial_tool(goal_planning_tool, {"user_id": user_id})
    goals_analysis = result.get('goals_analysis', {})

    # Return sample goals data matching the design
    return [
        {"id": "1", "name": "Emergency Fund", "targetAmount": 500000, "currentAmount": 410000, "percentage": 82, "monthlyContribution": 15000, "priority": "high"},
        {"id": "2", "name": "Home Down Payment", "targetAmount": 2000000, "currentAmount": 920000, "percentage": 46, "monthlyContribution": 25000, "priority": "high"},
        {"id": "3", "name": "Financial Freedom Corpus", "targetAmount": 32000000, "currentAmount": 10880000, "percentage": 34, "monthlyContribution": 50000, "priority": "high"},
    ]


@router.get("/data-confidence")
async def get_data_confidence(current_user: User = Depends(get_current_active_user)):
    """Data confidence score + items needing review"""
    return {
        "score": 87,
        "items": [
            {"label": "Monthly income", "source": "Salary slip • Aug 2026", "status": "verified"},
            {"label": "EPF balance", "source": "EPFO statement • Jun 2026", "status": "update"},
            {"label": "Monthly expenses", "source": "User estimate • May 2026", "status": "review"},
        ],
        "verifiedCount": 14,
        "estimateCount": 2,
        "outdatedCount": 1,
    }


@router.get("/documents")
async def get_documents(current_user: User = Depends(get_current_active_user)):
    """List uploaded documents with status"""
    return [
        {"id": "1", "name": "Salary Slip Aug 2026", "type": "salary_slip", "uploadedAt": "2026-08-15", "status": "verified"},
        {"id": "2", "name": "EPF Statement Jun 2026", "type": "epf_statement", "uploadedAt": "2026-07-01", "status": "verified"},
        {"id": "3", "name": "Form 16 FY 2025-26", "type": "form_16", "uploadedAt": "2026-06-15", "status": "pending"},
    ]

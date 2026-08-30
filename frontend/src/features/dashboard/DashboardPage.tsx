import React, { useState, useEffect } from 'react';
import { UserGreeting } from '@/components/dashboard/UserGreeting';
import { FinancialHealthScore } from '@/components/dashboard/FinancialHealthScore';
import { NetWorthCard } from '@/components/dashboard/NetWorthCard';
import { MonthlySurplusCard } from '@/components/dashboard/MonthlySurplusCard';
import { FreedomEstimateCard } from '@/components/dashboard/FreedomEstimateCard';
import { PathToFreedomPanel } from '@/components/dashboard/PathToFreedomPanel';
import { GoalsPanel } from '@/components/dashboard/GoalsPanel';
import { AskArthaPanel } from '@/components/dashboard/AskArthaPanel';
import { DataConfidencePanel } from '@/components/dashboard/DataConfidencePanel';
import { DocumentCompletionCard } from '@/components/dashboard/DocumentCompletionCard';

const DashboardPage: React.FC = () => {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate loading delay
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1500);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div data-testid="dashboard-page">
      {/* Greeting section */}
      <section className="section greeting">
        <div className="text">
          <UserGreeting name="Anita" />
        </div>
        <div className="score-card">
          <FinancialHealthScore score={68} />
        </div>
      </section>

      {/* Financial summary cards - three column grid */}
      <section className="section summary-grid">
        <div className="summary-grid">
          <NetWorthCard value="₹42.8L" change="↑ ₹64,000 this month" loading={loading} />
          <MonthlySurplusCard value="₹58,500" change="23% of take‑home pay" loading={loading} />
          <FreedomEstimateCard value="11 yr 4 mo" change="8 months sooner than baseline" loading={loading} />
        </div>
      </section>

      {/* Main content area - 65/35 grid */}
      <section className="section main-grid">
        <div className="main-grid">
          {/* Left column (65%) - Path to Freedom and Goals */}
          <div className="left-col">
            <PathToFreedomPanel
              currentCorpus="₹42.8L"
              targetCorpus="₹3.2Cr"
              progressPercent={34}
              freedomDate="Jan 2035"
            />
            <GoalsPanel
              goals={[
                { name: "Emergency Fund", percentage: 82 },
                { name: "Home Down Payment", percentage: 46 },
                { name: "Financial Freedom Corpus", percentage: 34 }
              ]}
            />
          </div>

          {/* Right column (35%) - Ask Artha, Data Confidence, Document Completion */}
          <div className="right-col">
            <AskArthaPanel
              placeholder="Ask about your finances…"
              buttonText="Send"
              chips={[
                "What’s my net worth?",
                "How much can I invest monthly?",
                "When will I be financially free?"
              ]}
            />
            <DataConfidencePanel
              confidenceScore={87}
              itemsReviewed="2"
              dataItems={[
                { name: "Monthly income", source: "Salary slip • Aug 2026", status: "verified" },
                { name: "EPF balance", source: "EPFO statement • Jun 2026", status: "update" },
                { name: "Monthly expenses", source: "User estimate • May 2026", status: "review" }
              ]}
            />
            <DocumentCompletionCard
              documentName="EPF statement"
              actionText="Upload"
              onUpload={() => alert('Upload clicked')}
              steps={[
                { label: "Uploaded", iconName: "check", completed: true },
                { label: "Securely processing", iconName: "loader", completed: false },
                { label: "Data extracted", iconName: "clipboard-type", completed: false },
                { label: "Waiting for confirmation", iconName: "circle-help", completed: false },
                { label: "Verified and added", iconName: "check-circle", completed: false }
              ]}
            />
          </div>
        </div>
      </section>
    </div>
  );
};

export default DashboardPage;
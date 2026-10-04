import type { ReactNode } from 'react';

const inlinePattern = /\*\*([^*]+)\*\*|\[([^\]]+)\]\((https:\/\/[^\s)]+)\)/g;

export function sourceLabel(url: string): string {
  try {
    const host = new URL(url).hostname.replace(/^www\./, '');
    const isDomain = (domain: string) => host === domain || host.endsWith(`.${domain}`);
    if (isDomain('rbi.org.in')) return 'RBI source';
    if (isDomain('sebi.gov.in')) return 'SEBI source';
    if (isDomain('pfrda.org.in')) return 'PFRDA source';
    if (isDomain('incometax.gov.in')) return 'Income Tax source';
    if (isDomain('irdai.gov.in') || isDomain('policyholder.gov.in')) return 'IRDAI source';
    return `${host} source`;
  } catch {
    return 'Source';
  }
}

function inlineContent(text: string, prefix: string): ReactNode[] {
  const parts: ReactNode[] = [];
  let position = 0;
  for (const match of text.matchAll(inlinePattern)) {
    const index = match.index ?? 0;
    if (index > position) parts.push(text.slice(position, index));
    if (match[1]) {
      parts.push(<strong key={`${prefix}-${index}`}>{match[1]}</strong>);
    } else {
      parts.push(<a key={`${prefix}-${index}`} href={match[3]} target="_blank" rel="noopener noreferrer" aria-label={`Open ${sourceLabel(match[3])} in a new tab`}>{sourceLabel(match[3])}</a>);
    }
    position = index + match[0].length;
  }
  if (position < text.length) parts.push(text.slice(position));
  return parts;
}

export default function ResponseText({ text }: { text: string }) {
  const blocks: ReactNode[] = [];
  let bullets: ReactNode[] = [];
  const flushBullets = () => {
    if (bullets.length) {
      blocks.push(<ul key={`list-${blocks.length}`}>{bullets}</ul>);
      bullets = [];
    }
  };
  for (const [index, rawLine] of text.replace(/\r\n/g, '\n').split('\n').entries()) {
    const line = rawLine.trim();
    if (!line) {
      flushBullets();
      continue;
    }
    if (/^[-*]\s+/.test(line)) {
      bullets.push(<li key={`item-${index}`}>{inlineContent(line.slice(2), `item-${index}`)}</li>);
    } else {
      flushBullets();
      blocks.push(<p key={`paragraph-${index}`}>{inlineContent(line, `paragraph-${index}`)}</p>);
    }
  }
  flushBullets();
  return <div className="message-content">{blocks}</div>;
}

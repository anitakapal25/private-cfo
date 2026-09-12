import { QRCodeSVG } from 'qrcode.react';

export interface MfaEnrollment {
  secret: string;
  issuer: string;
  account_name: string;
}

export default function MfaSetup({ enrollment }: { enrollment: MfaEnrollment }) {
  const { secret, issuer, account_name: accountName } = enrollment;
  const parameters = new URLSearchParams({ secret, issuer, algorithm: 'SHA1', digits: '6', period: '30' });
  const uri = `otpauth://totp/${encodeURIComponent(issuer)}:${encodeURIComponent(accountName)}?${parameters}`;

  return <div>
    <p>Scan this QR code with your authenticator app, then enter its six-digit code below.</p>
    <QRCodeSVG value={uri} size={240} marginSize={4} level="M"
      role="img" title="Scan to set up your authenticator"
      style={{ display: 'block', maxWidth: '100%', height: 'auto', margin: '16px auto' }} />
    <details>
      <summary>Can’t scan? Enter a setup key instead</summary>
      <p>Choose a time-based code in your authenticator app and enter this key:</p>
      <code style={{ overflowWrap: 'anywhere' }}>{secret}</code>
    </details>
  </div>;
}

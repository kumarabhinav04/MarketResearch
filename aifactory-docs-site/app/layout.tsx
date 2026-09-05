import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] });
const geistMono = Geist_Mono({ variable: '--font-geist-mono', subsets: ['latin'] });
const metadataOrigin = new URL(
  process.env.NEXT_PUBLIC_SITE_URL ||
    'https://ai-factory-research-handbook.kumar1365.chatgpt.site',
);

export const metadata: Metadata = {
  metadataBase: metadataOrigin,
  title: 'AI Factory Research Platform — Implementation Handbook',
  description: 'Architecture, agents, data sources, scoring, guardrails, telemetry, storage, operations, and user workflows for the AI Factory Growth Research Platform.',
  openGraph: {
    title: 'AI Factory Research Platform',
    description: 'Implementation Handbook — architecture, data, agents, scoring, guardrails and operations.',
    type: 'website',
    images: [{ url: new URL('/og.png', metadataOrigin), width: 1200, height: 630, alt: 'AI Factory Research Platform Implementation Handbook' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'AI Factory Research Platform',
    description: 'Implementation Handbook — architecture, data, agents, scoring, guardrails and operations.',
    images: [new URL('/og.png', metadataOrigin)],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>{children}</body></html>;
}

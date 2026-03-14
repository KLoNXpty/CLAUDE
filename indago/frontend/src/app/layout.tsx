import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Toaster } from "@/components/ui/toaster";

export const metadata: Metadata = {
  title: "INDAGO Evidence Capture | Digital Evidence Preservation Platform",
  description:
    "Professional digital evidence capture and preservation platform for forensic investigators. ISO/IEC 27037 compliant.",
  keywords: ["digital forensics", "evidence capture", "chain of custody", "ISO 27037", "WARC"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0a0e1a] text-slate-200 antialiased">
        <Providers>
          {children}
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}

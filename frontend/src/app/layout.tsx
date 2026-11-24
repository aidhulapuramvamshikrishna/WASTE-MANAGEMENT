import type { Metadata } from "next";
import localFont from "next/font/local";
import { headers } from "next/headers";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { ThemeProvider } from "@/components/ThemeProvider";
import "./globals.css";

const archivo = localFont({
  src: [
    {
      path: "./fonts/archivo-latin-wdth-normal.woff2",
      style: "normal",
    },
    {
      path: "./fonts/archivo-latin-wdth-italic.woff2",
      style: "italic",
    },
  ],
  variable: "--font-archivo",
  display: "swap",
});

const jetbrainsMono = localFont({
  src: [
    {
      path: "./fonts/jetbrains-mono-latin-wght-normal.woff2",
      style: "normal",
    },
    {
      path: "./fonts/jetbrains-mono-latin-wght-italic.woff2",
      style: "italic",
    },
  ],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "EcoSort — Municipal Waste Classification",
  description:
    "Which bin? Know in a second. Field instrument for four-stream municipal solid waste segregation powered by CNN vision and Grad-CAM explainability.",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // Reading headers signals to Next.js to apply dynamic CSP nonce if configured
  const headerList = await headers();
  void headerList.get("x-nonce");

  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${archivo.variable} ${jetbrainsMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col font-sans bg-[var(--paper)] text-[var(--ink)] transition-colors selection:bg-[var(--hivis)] selection:text-[#0E1A16]">
        <ThemeProvider>
          <Navbar />
          <div className="flex-1 flex flex-col">{children}</div>
          <Footer />
        </ThemeProvider>
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "UN Data Commons — Trust & Viability Copilot",
  description: "Ground-truth trust filter for development data queries",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="antialiased">
      <body className="flex flex-col bg-gray-100">
        <Header />
        <main className="flex-1 pt-16 pb-14">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}

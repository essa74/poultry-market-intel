import type { Metadata } from "next";
import { Cairo } from "next/font/google";
import "@/styles/globals.css";
import ClientLayout from "./client-layout";
import Providers from "./providers";

const cairo = Cairo({
  subsets: ["arabic", "latin"],
  variable: "--font-cairo",
  display: "swap",
  weight: ["300", "400", "500", "600", "700", "800", "900"],
});

export const metadata: Metadata = {
  title: "منصة ذكاء أسواق الدواجن — Poultry Market Intel",
  description:
    "منصة متكاملة لتحليل أسواق البيض المخصب وكتاكيت عمر يوم في مصر. تتبع الأسعار، تحليل الاتجاهات، واكتشاف التأثيرات الموسمية باستخدام الذكاء الاصطناعي.",
  keywords: ["دواجن", "بيض مخصب", "كتاكيت", "أسعار", "ذكاء اصطناعي", "السوق المصري", "poultry", "eggs", "Egypt"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl" className={`${cairo.variable}`}>
      <body className="min-h-screen bg-surface overflow-x-hidden">
        <Providers>
          <ClientLayout>{children}</ClientLayout>
        </Providers>
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Sales Excellence Platform",
  description: "Appraisal-to-listing performance platform for real estate teams"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

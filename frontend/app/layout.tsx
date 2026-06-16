import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "일짜곰 — 내가 만드는 이야기책",
  description:
    "아이가 직접 이야기를 만들고, AI가 결말을 비밀로 펼치며, 교사가 학급 단위로 학습 목표를 발제하는 어린이 도서 플랫폼.",
};

export const viewport: Viewport = {
  themeColor: "#f5872e",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className="h-full antialiased">
      <head>
        {/* Pretendard (한글 가독성) — 동적 서브셋 CDN */}
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
        />
      </head>
      <body className="min-h-full flex flex-col bg-background text-foreground">
        {children}
      </body>
    </html>
  );
}

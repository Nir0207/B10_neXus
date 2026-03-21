import type { Metadata } from "next";
import "./globals.css";
import Providers from "@/components/Providers";

export const metadata: Metadata = {
  title: "Genomic Visualization Portal",
  description: "BioNexus UI Portal",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
          rel="stylesheet"
        />
      </head>
      <body
        className="text-on-surface overflow-hidden h-screen flex flex-col bg-background"
      >
        <Providers>
          {/* Top Navigation Shell */}
          <header className="flex justify-between items-center w-full px-6 h-14 z-50 bg-background">
            <div className="flex items-center gap-8">
              <span className="text-xl font-bold tracking-tighter text-primary font-headline" data-testid="brand-primary">
                Genomic Portal
              </span>
              <div className="hidden md:flex items-center gap-6">
                <a
                  className="text-primary border-b-2 border-primary pb-1 text-sm font-medium transition-colors duration-150"
                  href="#"
                >
                  Explorer
                </a>
                <a
                  className="text-on-surface-variant hover:text-primary text-sm font-medium transition-colors duration-150"
                  href="#"
                >
                  Pathways
                </a>
                <a
                  className="text-on-surface-variant hover:text-primary text-sm font-medium transition-colors duration-150"
                  href="#"
                >
                  Clinical Trials
                </a>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="relative group">
                <span className="material-symbols-outlined text-on-surface-variant hover:bg-surface-bright p-1.5 rounded-full cursor-pointer transition-colors">
                  notifications
                </span>
                <span className="absolute top-1 right-1 w-2 h-2 bg-primary rounded-full"></span>
              </div>
              <span className="material-symbols-outlined text-on-surface-variant hover:bg-surface-bright p-1.5 rounded-full cursor-pointer transition-colors">
                settings
              </span>
              <div className="w-8 h-8 rounded-full overflow-hidden border border-outline-variant/30">
                <img
                  alt="User Scientist Profile"
                  className="w-full h-full object-cover"
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuCmxVZLGDrfvI_r6TD71gmjDvydc1bR3p82OfqadUmW3Db1kOjDvDvnzwKolFPcjNwehMbi52sqtp-_NONMP0U4T-sMzpAvW31tJ0kiTN9Mt4t17kD4AKS_1u5v0VlV2MFsqcNMr_SZGYpPZiWdDJH3GGfYaagRDJXBnD5SHnsTlx-b5R7Z2IRQtT-SQRT1P9vRd1yU6sv87nhf73lKhIqXvZEebDK1D8kfhQiEdpXyg1_B-4bidhVWXcZSvHCCJ9bl8GXmAlIu2b9s"
                />
              </div>
            </div>
          </header>
          <div className="flex flex-1 overflow-hidden">{children}</div>
        </Providers>
      </body>
    </html>
  );
}

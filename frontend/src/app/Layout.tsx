import { Suspense } from "react";
import { Outlet } from "react-router-dom";
import {
  Banner,
  Navigation,
  PageLoader,
} from "../components/common";
import { ToastProvider } from "../contexts/ToastContext";

export function Layout() {
  return (
    <ToastProvider>
      <div className="min-h-screen bg-surface">
        <Banner />
        <Navigation />

        <main role="main">
          <Suspense fallback={<PageLoader />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </ToastProvider>
  );
}


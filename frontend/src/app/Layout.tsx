import { Suspense } from "react";
import { Outlet } from "react-router-dom";
import {
  Banner,
  Navigation,
  ToastContainer,
  PageLoader,
} from "../components/common";
import { useToast } from "../hooks/useToast";

export function Layout() {
  const { toasts, close } = useToast();

  return (
    <div className="min-h-screen bg-gray-50">
      <Banner />
      <Navigation />

      <main role="main">
        <Suspense fallback={<PageLoader />}>
          <Outlet />
        </Suspense>
      </main>

      <ToastContainer toasts={toasts} onClose={close} />
    </div>
  );
}

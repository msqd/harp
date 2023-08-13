import { Outlet } from "react-router-dom";
import NavBar from "./NavBar.tsx";

function Layout() {
  return (
    <>
      <NavBar />
      <div className="mx-auto max-w-7xl px-2 sm:px-6 lg:px-8">
        Layout: <Outlet />
      </div>
    </>
  );
}

export default Layout;

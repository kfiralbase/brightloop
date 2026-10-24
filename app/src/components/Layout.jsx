import { Link } from "@tanstack/react-router";
import { CalendarDays, FlaskConical, History, ListChecks } from "lucide-react";
import HeaderStatus from "@/components/HeaderStatus";

const NAV = [
  { to: "/", label: "This week", icon: CalendarDays },
  { to: "/history", label: "History", icon: History },
  { to: "/runs", label: "Runs", icon: ListChecks },
  { to: "/test", label: "Test a file", icon: FlaskConical },
];

export default function Layout({ children }) {
  return (
    <div className="min-h-screen bg-white pb-20 md:pb-0">
      <header className="sticky top-0 z-30 border-b border-[#E2E8F0] bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center gap-6 px-4 md:px-8">
          <Link to="/" className="font-display text-base font-extrabold tracking-tight text-[#0F172A] md:text-lg">
            Brightloop Pricing Watch
          </Link>
          <nav className="hidden items-center gap-1 md:flex">
            {NAV.map((n) => (
              <Link key={n.to} to={n.to} activeOptions={{ exact: n.to === "/" }}
                className="rounded-lg px-3 py-2 text-sm font-medium text-[#64748B] hover:bg-[#F8FAFC] hover:text-[#0F172A]"
                activeProps={{ className: "bg-[#F8FAFC] !text-[#0F172A]" }}>
                {n.label}
              </Link>
            ))}
          </nav>
          <div className="ml-auto"><HeaderStatus /></div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 md:px-8 md:py-10">{children}</main>
      <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 border-t border-[#E2E8F0] bg-white md:hidden">
        {NAV.map((n) => (
          <Link key={n.to} to={n.to} activeOptions={{ exact: n.to === "/" }}
            className="flex h-16 flex-col items-center justify-center gap-1 text-xs font-medium text-[#64748B]"
            activeProps={{ className: "!text-[#4F46E5]" }}>
            <n.icon className="h-5 w-5" />
            {n.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
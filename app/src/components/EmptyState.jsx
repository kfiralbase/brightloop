export default function EmptyState({ title, text }) {
  return (
    <div className="rounded-lg border border-dashed border-[#E2E8F0] p-8 text-center md:p-12">
      <p className="font-display text-lg font-bold text-[#0F172A]">{title}</p>
      {text && <p className="mx-auto mt-2 max-w-md text-[#64748B]">{text}</p>}
    </div>
  );
}
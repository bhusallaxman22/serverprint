import { Badge } from "@/components/atoms/Badge";

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={status}>{status}</Badge>;
}

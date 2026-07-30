import { redirect } from "next/navigation";
import { getSession } from "@/lib/auth/session";
import { LoginTemplate } from "@/components/templates/LoginTemplate";

export default async function LoginPage() {
  const session = await getSession();
  if (session.isLoggedIn) redirect("/dashboard");
  return <LoginTemplate />;
}

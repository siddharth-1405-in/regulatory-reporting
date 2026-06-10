"use client";
import { createContext, useContext, useEffect, useState } from "react";

export type Role = "Maker" | "Checker" | "Admin";

type Ctx = { role: Role; setRole: (r: Role) => void; actor: string };
const RoleCtx = createContext<Ctx>({ role: "Checker", setRole: () => {}, actor: "checker.user" });

const ACTOR: Record<Role, string> = {
  Maker: "maker.user", Checker: "checker.user", Admin: "admin.user",
};

export function RoleProvider({ children }: { children: React.ReactNode }) {
  const [role, setRoleState] = useState<Role>("Checker");
  useEffect(() => {
    const saved = localStorage.getItem("car.role") as Role | null;
    if (saved) setRoleState(saved);
  }, []);
  const setRole = (r: Role) => { setRoleState(r); localStorage.setItem("car.role", r); };
  return <RoleCtx.Provider value={{ role, setRole, actor: ACTOR[role] }}>{children}</RoleCtx.Provider>;
}

export const useRole = () => useContext(RoleCtx);

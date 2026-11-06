import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext } from "react";
import type { User } from "./types";
export const Auth = createContext<{
  user: User;
  canManage: boolean;
  canOperate: boolean;
}>({ user: {} as User, canManage: false, canOperate: false });
export const Toast = createContext<(s: string) => void>(() => {});
export function useAction<T = unknown>(
  fn: (v: T) => Promise<unknown>,
  success = "Changes saved",
) {
  const qc = useQueryClient();
  const toast = useContext(Toast);
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      qc.invalidateQueries();
      toast(success);
    },
  });
}

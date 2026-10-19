import { createContext, useContext } from "react";
import type { Scope } from "./api";
export const Workspace = createContext<{
  scope: Scope;
  refresh: () => void;
  setDirty: (dirty: boolean) => void;
}>(null!);
export const useWorkspace = () => useContext(Workspace);

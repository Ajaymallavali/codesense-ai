import { Router, Request, Response } from "express";
import { findUserByEmail, listActiveAccounts } from "../db/queries";

export const userRouter = Router();

userRouter.get("/search", async (req: Request, res: Response) => {
  const email = req.query.email as string;
  const user = await findUserByEmail(email);
  if (!user) {
    return res.status(404).json({ error: "User not found" });
  }
  return res.json({ user });
});

userRouter.get("/accounts", async (req: Request, res: Response) => {
  const accounts = await listActiveAccounts();
  return res.json({ accounts });
});

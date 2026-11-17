import express, { Request, Response } from "express";
import { userRouter } from "./routes/users";

const app = express();
app.use(express.json());

app.get("/health", (req: Request, res: Response) => {
  res.json({ service: "node-express-sql-service", status: "HEALTHY" });
});

app.use("/api/users", userRouter);

export default app;

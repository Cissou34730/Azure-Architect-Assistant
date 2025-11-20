import { Router } from "express";
// import { router as itemsRouter } from "./items.js";  // Disabled for POC
import { router as projectsRouter } from "./projects.js";

export const apiRouter = Router();

// apiRouter.use(itemsRouter);  // Disabled for POC
apiRouter.use(projectsRouter);

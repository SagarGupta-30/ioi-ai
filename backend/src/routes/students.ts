import { Router, Request, Response } from "express";
import { StudentModel } from "../models/student.model";

export const studentsRouter = Router();

// ---------------------------------------------------------------------------
// GET /api/students
// Supports: search, campus, batch, gender filtering + pagination
// ---------------------------------------------------------------------------
studentsRouter.get("/students", async (req: Request, res: Response) => {
  try {
    const { search, campus, batch, gender, page, limit } = req.query;

    // -- Validate gender ---------------------------------------------------
    if (gender && gender !== "MALE" && gender !== "FEMALE") {
      res.status(400).json({
        success: false,
        message: 'Invalid gender value. Must be "MALE" or "FEMALE".',
      });
      return;
    }

    // -- Validate & normalize pagination -----------------------------------
    const MAX_LIMIT = 100;
    const DEFAULT_LIMIT = 20;

    let pageNum = parseInt(page as string, 10);
    let limitNum = parseInt(limit as string, 10);

    if (isNaN(pageNum) || pageNum < 1) pageNum = 1;
    if (isNaN(limitNum) || limitNum < 1) limitNum = DEFAULT_LIMIT;
    if (limitNum > MAX_LIMIT) limitNum = MAX_LIMIT;

    // -- Build MongoDB query filter ----------------------------------------
    const filter: Record<string, unknown> = {};

    if (search && typeof search === "string" && search.trim()) {
      filter.name = { $regex: search.trim(), $options: "i" };
    }
    if (campus && typeof campus === "string") {
      filter.campus = campus;
    }
    if (batch && typeof batch === "string") {
      filter.batch = batch;
    }
    if (gender) {
      filter.gender = gender;
    }

    // -- Execute query with pagination -------------------------------------
    const skip = (pageNum - 1) * limitNum;

    const [students, total] = await Promise.all([
      StudentModel.find(filter).skip(skip).limit(limitNum),
      StudentModel.countDocuments(filter),
    ]);

    const totalPages = Math.ceil(total / limitNum);

    res.json({
      success: true,
      count: students.length,
      total,
      page: pageNum,
      limit: limitNum,
      totalPages,
      data: students,
    });
  } catch (error) {
    console.error("[students] Failed to fetch students:", error);
    res.status(500).json({
      success: false,
      error: "Failed to fetch students",
    });
  }
});

// ---------------------------------------------------------------------------
// GET /api/students/:id
// Returns a single student by their PW IOI UUID (stored as studentId)
// ---------------------------------------------------------------------------
studentsRouter.get("/students/:id", async (req: Request, res: Response) => {
  try {
    const student = await StudentModel.findOne({ studentId: req.params.id });

    if (!student) {
      res.status(404).json({
        success: false,
        message: "Student not found",
      });
      return;
    }

    res.json({
      success: true,
      data: student,
    });
  } catch (error) {
    console.error("[students] Failed to fetch student:", error);
    res.status(500).json({
      success: false,
      error: "Failed to fetch student",
    });
  }
});
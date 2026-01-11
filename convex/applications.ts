import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

// Create application
export const createApplication = mutation({
  args: {
    jobId: v.id("jobs"),
    resumeId: v.id("resumes"),
    status: v.string(),
    notes: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("applications", {
      ...args,
      appliedAt: args.status === "applied" ? Date.now() : undefined,
    });
  },
});

// Update application status
export const updateApplicationStatus = mutation({
  args: {
    applicationId: v.id("applications"),
    status: v.string(),
  },
  handler: async (ctx, args) => {
    const updates: any = { status: args.status };

    // Set appliedAt timestamp when status changes to "applied"
    if (args.status === "applied") {
      updates.appliedAt = Date.now();
    }

    await ctx.db.patch(args.applicationId, updates);
  },
});

// Get all applications
export const getApplications = query({
  handler: async (ctx) => {
    const applications = await ctx.db
      .query("applications")
      .order("desc")
      .collect();

    // Join with job data
    return await Promise.all(
      applications.map(async (app) => {
        const job = await ctx.db.get(app.jobId);
        return {
          ...app,
          job,
        };
      })
    );
  },
});

import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

// Create or update job (upsert by URL)
export const upsertJob = mutation({
  args: {
    title: v.string(),
    company: v.string(),
    location: v.string(),
    salary: v.optional(v.string()),
    shortDescription: v.string(),
    fullDescription: v.string(),
    url: v.string(),
    source: v.string(),
  },
  handler: async (ctx, args) => {
    // Check if job exists by URL
    const existing = await ctx.db
      .query("jobs")
      .withIndex("by_url", (q) => q.eq("url", args.url))
      .first();

    if (existing) {
      // Update existing job
      await ctx.db.patch(existing._id, {
        ...args,
        scrapedAt: Date.now(),
      });
      return { jobId: existing._id, isNew: false };
    } else {
      // Create new job
      const jobId = await ctx.db.insert("jobs", {
        ...args,
        scrapedAt: Date.now(),
        status: "active",
      });
      return { jobId, isNew: true };
    }
  },
});

// Get all active jobs
export const getActiveJobs = query({
  args: {
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const jobs = await ctx.db
      .query("jobs")
      .withIndex("by_status", (q) => q.eq("status", "active"))
      .order("desc")
      .take(args.limit || 100);

    return jobs;
  },
});

// Get single job with match data
export const getJobWithMatch = query({
  args: { jobId: v.id("jobs") },
  handler: async (ctx, args) => {
    const job = await ctx.db.get(args.jobId);
    if (!job) return null;

    // Get latest match for this job
    const match = await ctx.db
      .query("jobMatches")
      .withIndex("by_job", (q) => q.eq("jobId", args.jobId))
      .order("desc")
      .first();

    // Get application if exists
    const application = await ctx.db
      .query("applications")
      .withIndex("by_job", (q) => q.eq("jobId", args.jobId))
      .first();

    return {
      ...job,
      matchData: match || null,
      application: application || null,
    };
  },
});

// Delete old jobs (cleanup)
export const deleteOldJobs = mutation({
  args: { daysOld: v.number() },
  handler: async (ctx, args) => {
    const cutoffDate = Date.now() - args.daysOld * 24 * 60 * 60 * 1000;

    const oldJobs = await ctx.db
      .query("jobs")
      .withIndex("by_scraped_at")
      .filter((q) => q.lt(q.field("scrapedAt"), cutoffDate))
      .collect();

    let deletedCount = 0;
    for (const job of oldJobs) {
      // Don't delete if there's an application
      const hasApplication = await ctx.db
        .query("applications")
        .withIndex("by_job", (q) => q.eq("jobId", job._id))
        .first();

      if (!hasApplication) {
        // Delete related matches first
        const matches = await ctx.db
          .query("jobMatches")
          .withIndex("by_job", (q) => q.eq("jobId", job._id))
          .collect();

        for (const match of matches) {
          await ctx.db.delete(match._id);
        }

        // Delete job
        await ctx.db.delete(job._id);
        deletedCount++;
      }
    }

    return { deletedCount };
  },
});

// Archive a job
export const archiveJob = mutation({
  args: { jobId: v.id("jobs") },
  handler: async (ctx, args) => {
    await ctx.db.patch(args.jobId, { status: "archived" });
  },
});

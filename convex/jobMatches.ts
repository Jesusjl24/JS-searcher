import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

// Save job match score
export const saveJobMatch = mutation({
  args: {
    jobId: v.id("jobs"),
    resumeId: v.id("resumes"),
    score: v.number(),
    reasoning: v.string(),
    pros: v.array(v.string()),
    cons: v.array(v.string()),
    gaps: v.array(v.string()),
    strongMatches: v.array(v.string()),
    recommendation: v.string(),
    strategicConsiderations: v.array(v.string()),
  },
  handler: async (ctx, args) => {
    // Check if match already exists
    const existing = await ctx.db
      .query("jobMatches")
      .withIndex("by_job_and_resume", (q) =>
        q.eq("jobId", args.jobId).eq("resumeId", args.resumeId)
      )
      .first();

    if (existing) {
      // Update existing match
      await ctx.db.patch(existing._id, {
        ...args,
        scoredAt: Date.now(),
      });
      return existing._id;
    } else {
      // Create new match
      return await ctx.db.insert("jobMatches", {
        ...args,
        scoredAt: Date.now(),
      });
    }
  },
});

// Get high-scoring matches
export const getHighMatches = query({
  args: { threshold: v.number() },
  handler: async (ctx, args) => {
    const matches = await ctx.db
      .query("jobMatches")
      .withIndex("by_score")
      .filter((q) => q.gte(q.field("score"), args.threshold))
      .order("desc")
      .take(50);

    // Join with job data
    const matchesWithJobs = await Promise.all(
      matches.map(async (match) => {
        const job = await ctx.db.get(match.jobId);
        return {
          ...match,
          job,
        };
      })
    );

    return matchesWithJobs;
  },
});

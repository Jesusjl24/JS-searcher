import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

// Create new resume (sets as active)
export const createResume = mutation({
  args: {
    name: v.string(),
    content: v.string(),
    skills: v.array(v.string()),
    experienceYears: v.number(),
    education: v.array(v.string()),
    previousTitles: v.array(v.string()),
    industries: v.array(v.string()),
    achievements: v.array(v.string()),
    preferredRoles: v.array(v.string()),
    location: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    // Deactivate all other resumes
    const activeResumes = await ctx.db
      .query("resumes")
      .withIndex("by_active", (q) => q.eq("isActive", true))
      .collect();

    for (const resume of activeResumes) {
      await ctx.db.patch(resume._id, { isActive: false });
    }

    // Create new active resume
    return await ctx.db.insert("resumes", {
      ...args,
      isActive: true,
      createdAt: Date.now(),
    });
  },
});

// Get active resume
export const getActiveResume = query({
  handler: async (ctx) => {
    return await ctx.db
      .query("resumes")
      .withIndex("by_active", (q) => q.eq("isActive", true))
      .first();
  },
});

// Get all resumes
export const getAllResumes = query({
  handler: async (ctx) => {
    return await ctx.db
      .query("resumes")
      .order("desc")
      .collect();
  },
});

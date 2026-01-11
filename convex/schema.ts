import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  // Jobs table
  jobs: defineTable({
    title: v.string(),
    company: v.string(),
    location: v.string(),
    salary: v.optional(v.string()),
    shortDescription: v.string(),
    fullDescription: v.string(),
    url: v.string(),
    source: v.string(), // "SEEK"
    scrapedAt: v.number(), // Unix timestamp
    status: v.string(), // "active", "archived"
  })
    .index("by_url", ["url"]) // For deduplication
    .index("by_status", ["status"])
    .index("by_scraped_at", ["scrapedAt"]),

  // Job matches (scoring results)
  jobMatches: defineTable({
    jobId: v.id("jobs"),
    resumeId: v.id("resumes"),
    score: v.number(), // 0-100
    reasoning: v.string(),
    pros: v.array(v.string()),
    cons: v.array(v.string()),
    gaps: v.array(v.string()),
    strongMatches: v.array(v.string()),
    recommendation: v.string(),
    strategicConsiderations: v.array(v.string()),
    scoredAt: v.number(),
  })
    .index("by_job", ["jobId"])
    .index("by_resume", ["resumeId"])
    .index("by_score", ["score"])
    .index("by_job_and_resume", ["jobId", "resumeId"]),

  // Resumes (version control)
  resumes: defineTable({
    name: v.string(),
    content: v.string(), // Full text
    skills: v.array(v.string()),
    experienceYears: v.number(),
    education: v.array(v.string()),
    previousTitles: v.array(v.string()),
    industries: v.array(v.string()),
    achievements: v.array(v.string()),
    preferredRoles: v.array(v.string()),
    location: v.optional(v.string()),
    isActive: v.boolean(),
    createdAt: v.number(),
  }).index("by_active", ["isActive"]),

  // Applications (track what you applied to)
  applications: defineTable({
    jobId: v.id("jobs"),
    resumeId: v.id("resumes"),
    status: v.string(), // "interested", "applied", "interview", "rejected", "offer"
    appliedAt: v.optional(v.number()),
    notes: v.optional(v.string()),
  })
    .index("by_job", ["jobId"])
    .index("by_status", ["status"]),
});

"""
Convex Client Wrapper for Job Search Application

This module provides a Python interface to interact with the Convex backend.
All database operations go through this client.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from convex import ConvexClient

logger = logging.getLogger(__name__)


class JobSearchConvexClient:
    """
    Wrapper around Convex client for job search operations.

    Provides methods for managing jobs, resumes, job matches, and applications.
    """

    def __init__(self, deployment_url: Optional[str] = None):
        """
        Initialize Convex client.

        Args:
            deployment_url: Convex deployment URL. If not provided, reads from CONVEX_URL env var.
        """
        self.deployment_url = deployment_url or os.getenv("CONVEX_URL")

        if not self.deployment_url:
            raise ValueError(
                "CONVEX_URL not set. Please set the CONVEX_URL environment variable "
                "or pass deployment_url to the constructor."
            )

        try:
            self.client = ConvexClient(self.deployment_url)
            logger.info("Connected to Convex backend")
        except Exception as e:
            logger.error(f"Failed to connect to Convex: {e}")
            raise

    # ==================== JOBS ====================

    def upsert_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or update a job (upserts by URL).

        Args:
            job_data: Dictionary containing job fields:
                - title (str)
                - company (str)
                - location (str)
                - salary (str, optional)
                - shortDescription (str)
                - fullDescription (str)
                - url (str)
                - source (str, e.g., "SEEK")

        Returns:
            Dict with 'jobId' and 'isNew' (bool)
        """
        try:
            result = self.client.mutation("jobs:upsertJob", job_data)
            logger.debug(f"Upserted job: {job_data.get('title')} - New: {result.get('isNew')}")
            return result
        except Exception as e:
            logger.error(f"Error upserting job: {e}")
            raise

    def get_active_jobs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all active jobs.

        Args:
            limit: Maximum number of jobs to return (default 100)

        Returns:
            List of job dictionaries
        """
        try:
            jobs = self.client.query("jobs:getActiveJobs", {"limit": limit})
            logger.debug(f"Retrieved {len(jobs)} active jobs")
            return jobs
        except Exception as e:
            logger.error(f"Error getting active jobs: {e}")
            raise

    def get_job_with_match(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single job with its match data and application status.

        Args:
            job_id: Convex job ID

        Returns:
            Job dictionary with matchData and application, or None if not found
        """
        try:
            job = self.client.query("jobs:getJobWithMatch", {"jobId": job_id})
            return job
        except Exception as e:
            logger.error(f"Error getting job with match: {e}")
            raise

    def archive_job(self, job_id: str) -> None:
        """
        Archive a job (sets status to 'archived').

        Args:
            job_id: Convex job ID
        """
        try:
            self.client.mutation("jobs:archiveJob", {"jobId": job_id})
            logger.info(f"Archived job: {job_id}")
        except Exception as e:
            logger.error(f"Error archiving job: {e}")
            raise

    def delete_old_jobs(self, days_old: int = 30) -> Dict[str, int]:
        """
        Delete jobs older than specified days (keeps jobs with applications).

        Args:
            days_old: Delete jobs older than this many days

        Returns:
            Dict with 'deletedCount'
        """
        try:
            result = self.client.mutation("jobs:deleteOldJobs", {"daysOld": days_old})
            logger.info(f"Deleted {result['deletedCount']} old jobs")
            return result
        except Exception as e:
            logger.error(f"Error deleting old jobs: {e}")
            raise

    # ==================== JOB MATCHES ====================

    def save_job_match(self, match_data: Dict[str, Any]) -> str:
        """
        Save a job match score.

        Args:
            match_data: Dictionary containing:
                - jobId (str)
                - resumeId (str)
                - score (int, 0-100)
                - reasoning (str)
                - pros (list[str])
                - cons (list[str])
                - gaps (list[str])
                - strongMatches (list[str])
                - recommendation (str)
                - strategicConsiderations (list[str])

        Returns:
            Match ID
        """
        try:
            match_id = self.client.mutation("jobMatches:saveJobMatch", match_data)
            logger.debug(f"Saved job match with score {match_data.get('score')}")
            return match_id
        except Exception as e:
            logger.error(f"Error saving job match: {e}")
            raise

    def get_high_matches(self, threshold: int = 70) -> List[Dict[str, Any]]:
        """
        Get jobs with match score above threshold.

        Args:
            threshold: Minimum match score (0-100)

        Returns:
            List of matches with embedded job data
        """
        try:
            matches = self.client.query("jobMatches:getHighMatches", {"threshold": threshold})
            logger.debug(f"Retrieved {len(matches)} matches above {threshold}%")
            return matches
        except Exception as e:
            logger.error(f"Error getting high matches: {e}")
            raise

    # ==================== RESUMES ====================

    def create_resume(self, resume_data: Dict[str, Any]) -> str:
        """
        Create a new resume (automatically sets it as active).

        Args:
            resume_data: Dictionary containing:
                - name (str)
                - content (str)
                - skills (list[str])
                - experienceYears (int)
                - education (list[str])
                - previousTitles (list[str])
                - industries (list[str])
                - achievements (list[str])
                - preferredRoles (list[str])
                - location (str, optional)

        Returns:
            Resume ID
        """
        try:
            resume_id = self.client.mutation("resumes:createResume", resume_data)
            logger.info(f"Created resume: {resume_data.get('name')}")
            return resume_id
        except Exception as e:
            logger.error(f"Error creating resume: {e}")
            raise

    def get_active_resume(self) -> Optional[Dict[str, Any]]:
        """
        Get the currently active resume.

        Returns:
            Resume dictionary or None if no active resume
        """
        try:
            resume = self.client.query("resumes:getActiveResume", {})
            return resume
        except Exception as e:
            logger.error(f"Error getting active resume: {e}")
            raise

    def get_all_resumes(self) -> List[Dict[str, Any]]:
        """
        Get all resumes (active and inactive).

        Returns:
            List of resume dictionaries
        """
        try:
            resumes = self.client.query("resumes:getAllResumes", {})
            return resumes
        except Exception as e:
            logger.error(f"Error getting all resumes: {e}")
            raise

    # ==================== APPLICATIONS ====================

    def create_application(self, application_data: Dict[str, Any]) -> str:
        """
        Create a new job application.

        Args:
            application_data: Dictionary containing:
                - jobId (str)
                - resumeId (str)
                - status (str): "interested", "applied", "interview", "rejected", "offer"
                - notes (str, optional)

        Returns:
            Application ID
        """
        try:
            app_id = self.client.mutation("applications:createApplication", application_data)
            logger.info(f"Created application with status: {application_data.get('status')}")
            return app_id
        except Exception as e:
            logger.error(f"Error creating application: {e}")
            raise

    def update_application_status(self, application_id: str, status: str) -> None:
        """
        Update application status.

        Args:
            application_id: Convex application ID
            status: New status ("interested", "applied", "interview", "rejected", "offer")
        """
        try:
            self.client.mutation("applications:updateApplicationStatus", {
                "applicationId": application_id,
                "status": status
            })
            logger.info(f"Updated application {application_id} to status: {status}")
        except Exception as e:
            logger.error(f"Error updating application status: {e}")
            raise

    def get_applications(self) -> List[Dict[str, Any]]:
        """
        Get all applications with embedded job data.

        Returns:
            List of application dictionaries
        """
        try:
            applications = self.client.query("applications:getApplications", {})
            return applications
        except Exception as e:
            logger.error(f"Error getting applications: {e}")
            raise

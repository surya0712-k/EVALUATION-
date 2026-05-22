export type UserProfile = {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  job_title: string | null;
  bio: string | null;
  avatar_url: string | null;
  profile_complete: boolean;
};

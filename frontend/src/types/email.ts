// Mirrors backend/app/routes/email_prefs.py::EmailPreferencesResponse / EmailPreferencesUpdate

export interface EmailPreferences {
  daily_brief: boolean;
  watchlist_digest: boolean;
  weekly_recap: boolean;
  product_updates: boolean;
}

export type EmailPreferenceKey = keyof EmailPreferences;

/** All fields optional — only provided booleans are sent/updated. */
export type EmailPreferencesUpdate = Partial<EmailPreferences>;

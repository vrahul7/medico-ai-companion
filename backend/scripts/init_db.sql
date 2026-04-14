-- Create schema for telemetry logging
CREATE SCHEMA IF NOT EXISTS logging;

CREATE TABLE IF NOT EXISTS logging.telemetry_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users, -- Supabase standard auth linking
    session_id TEXT,
    event_type TEXT NOT NULL,           -- e.g., 'ddx_query', 'chat_query', 'citation_click', 'feedback_upvote'
    query_text TEXT,                    -- The anonymized query text
    response_text TEXT,                 -- The anonymized generated response
    retrieval_confidence FLOAT,         -- Confidence score for fallback auditing
    feedback_score INT,                 -- 1 for upvote, -1 for downvote, 0 for neutral
    feedback_text TEXT,                 -- Additional user feedback text
    metadata JSONB,                     -- Any extra schema for specific workflows (Age, Vitals input for DDx)
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Protect the logs using Row Level Security (RLS)
ALTER TABLE logging.telemetry_logs ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to insert their own telemetry
CREATE POLICY "Users can insert their own telemetry" 
    ON logging.telemetry_logs FOR INSERT 
    TO authenticated 
    WITH CHECK (auth.uid() = user_id);

-- Only admins (or specific roles) can view telemetry logs
CREATE POLICY "Admins can view telemetry logs" 
    ON logging.telemetry_logs FOR SELECT 
    TO authenticated 
    USING ( (current_setting('request.jwt.claims', true)::jsonb ->> 'role') = 'admin' );

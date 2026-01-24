-- Migration: Create notifications table
-- Run this SQL script on your database to create the notifications table and indexes
-- PostgreSQL syntax
-- This migration is idempotent - safe to run multiple times

-- Only create table if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'notifications') THEN
        CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    recipient_id INTEGER NOT NULL,
    actor_id INTEGER NOT NULL,
    post_id INTEGER NOT NULL,
    comment_id INTEGER,
    type VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP,
    FOREIGN KEY (recipient_id) REFERENCES users(id),
    FOREIGN KEY (actor_id) REFERENCES users(id),
    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (comment_id) REFERENCES comments(id)
        );
    END IF;
END $$;

-- Create indexes for efficient queries (only if they don't exist)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_notification_recipient') THEN
        CREATE INDEX idx_notification_recipient ON notifications(recipient_id);
    END IF;
    IF NOT EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_notification_post') THEN
        CREATE INDEX idx_notification_post ON notifications(post_id);
    END IF;
    IF NOT EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_notification_comment') THEN
        CREATE INDEX idx_notification_comment ON notifications(comment_id);
    END IF;
    IF NOT EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_notification_recipient_read') THEN
        CREATE INDEX idx_notification_recipient_read ON notifications(recipient_id, read_at);
    END IF;
    IF NOT EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_notification_recipient_post') THEN
        CREATE INDEX idx_notification_recipient_post ON notifications(recipient_id, post_id);
    END IF;
    IF NOT EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_notification_recipient_comment') THEN
        CREATE INDEX idx_notification_recipient_comment ON notifications(recipient_id, comment_id);
    END IF;
END $$;

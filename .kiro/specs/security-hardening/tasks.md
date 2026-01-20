# Implementation Plan: Security Hardening

## Overview

This implementation plan breaks down the security hardening feature into discrete, incremental coding tasks. Each task builds on previous work, with testing integrated throughout to validate functionality early. The implementation follows a layered approach: data models first, then core security components, followed by integration with existing authentication, and finally the admin dashboard.

## Tasks

- [x] 1. Set up security infrastructure and dependencies
  - Install required packages: Flask-Limiter, Flask-Talisman, PyOTP, qrcode, Hypothesis
  - Create security configuration module for environment variable loading
  - Set up security logging configuration
  - _Requirements: 11.1-11.8_

- [x] 2. Create database models and migration
  - [x] 2.1 Define LoginAttempt model with all required fields and indexes
    - Create model with id, user_id, username, ip_address, success, failure_reason, timestamp
    - Add indexes for timestamp, username, and ip_address
    - Add relationship to User model
    - _Requirements: 10.1, 10.5_
  
  - [x] 2.2 Define AuditLog model with all required fields and indexes
    - Create model with id, user_id, username, action_type, details, ip_address, timestamp
    - Add indexes for timestamp, user_id, and action_type
    - Add relationship to User model
    - _Requirements: 10.2, 10.6_
  
  - [x] 2.3 Define TwoFactorAuth model with all required fields
    - Create model with id, user_id, secret, enabled, backup_codes, created_at, last_used
    - Add unique constraint on user_id
    - Add relationship to User model
    - _Requirements: 10.3_
  
  - [x] 2.4 Extend User model with security fields
    - Add failed_login_attempts, locked_until, last_login_at fields
    - Add is_locked() helper method
    - Add reset_failed_attempts() helper method
    - _Requirements: 10.4_
  
  - [x] 2.5 Create database migration script
    - Generate migration for new tables and User model extensions
    - Test migration up and down
    - _Requirements: 10.1-10.4_
  
  - [x] 2.6 Write property test for automatic timestamp assignment
    - **Property 25: Automatic Timestamp Assignment**
    - **Validates: Requirements 10.5, 10.6**

- [x] 3. Implement Password Validator component
  - [x] 3.1 Create PasswordValidator class with configuration
    - Implement validation logic for all requirements (length, uppercase, lowercase, digit, special)
    - Implement get_requirements_text() method
    - Load configuration from environment variables
    - _Requirements: 5.1-5.7_
  
  - [x] 3.2 Write property test for password complexity validation
    - **Property 15: Password Complexity Validation**
    - **Validates: Requirements 5.1-5.6**
  
  - [x] 3.3 Write property test for password validation error completeness
    - **Property 27: Password Validation Error Completeness**
    - **Validates: Requirements 13.3**
  
  - [x] 3.4 Write unit tests for password validation edge cases
    - Test boundary conditions (exactly 12 characters)
    - Test each requirement individually
    - Test error message formatting
    - _Requirements: 5.1-5.7_

- [x] 4. Implement Rate Limiter component
  - [x] 4.1 Initialize Flask-Limiter with configuration
    - Configure storage backend (memory or Redis)
    - Load rate limits from environment variables
    - Apply decorators to login, admin, and password reset routes
    - _Requirements: 1.1-1.5_
  
  - [x] 4.2 Write property test for rate limiting enforcement
    - **Property 1: Rate Limiting Enforcement**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4**
  
  - [x] 4.3 Write unit tests for rate limiting edge cases
    - Test exact boundary (5th vs 6th request)
    - Test rate limit reset after time window
    - Test retry-after header calculation
    - _Requirements: 1.1-1.4_

- [x] 5. Implement Account Lockout Manager component
  - [x] 5.1 Create AccountLockoutManager class
    - Implement record_failed_attempt() method
    - Implement record_successful_login() method
    - Implement is_locked() method
    - Implement get_unlock_time() method
    - Implement unlock_account() method
    - Load configuration from environment variables
    - _Requirements: 2.1-2.5_
  
  - [x] 5.2 Write property test for account lockout after failed attempts
    - **Property 2: Account Lockout After Failed Attempts**
    - **Validates: Requirements 2.1, 2.2**
  
  - [x] 5.3 Write property test for account lockout expiration
    - **Property 3: Account Lockout Expiration**
    - **Validates: Requirements 2.3**
  
  - [x] 5.4 Write property test for failed attempt counter reset
    - **Property 4: Failed Attempt Counter Reset**
    - **Validates: Requirements 2.4**
  
  - [x] 5.5 Write unit tests for account lockout edge cases
    - Test lockout at exact threshold
    - Test lockout expiration at exact time
    - Test different threshold configurations
    - _Requirements: 2.1-2.5_

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement Audit Logger component
  - [x] 7.1 Create AuditLogger class
    - Implement log_login_attempt() method
    - Implement log_admin_action() method
    - Implement log_account_lockout() method
    - Implement log_2fa_change() method
    - Implement get_recent_logs() method with filtering
    - Implement get_login_attempts() method with filtering
    - _Requirements: 8.1-8.10_
  
  - [x] 7.2 Write property test for admin action audit logging
    - **Property 17: Admin Action Audit Logging**
    - **Validates: Requirements 8.1-8.6**
  
  - [x] 7.3 Write property test for login attempt recording
    - **Property 18: Login Attempt Recording**
    - **Validates: Requirements 8.7, 8.8**
  
  - [x] 7.4 Write property test for security event audit logging
    - **Property 19: Security Event Audit Logging**
    - **Validates: Requirements 8.9, 8.10**
  
  - [x] 7.5 Write property test for lockout event logging
    - **Property 5: Lockout Event Logging**
    - **Validates: Requirements 2.6**
  
  - [x] 7.6 Write unit tests for audit logging
    - Test each action type creates correct log entry
    - Test filtering by date, user, action type
    - Test pagination
    - _Requirements: 8.1-8.10_

- [x] 8. Implement Two-Factor Authentication Manager component
  - [x] 8.1 Create TwoFactorAuthManager class
    - Implement generate_secret() method
    - Implement get_provisioning_uri() method
    - Implement verify_totp() method
    - Implement enable_2fa() method
    - Implement disable_2fa() method
    - Implement generate_backup_codes() method
    - Implement verify_backup_code() method
    - Implement is_enabled() method
    - _Requirements: 3.1-3.7_
  
  - [x] 8.2 Write property test for 2FA secret generation
    - **Property 6: 2FA Secret Generation**
    - **Validates: Requirements 3.1**
  
  - [x] 8.3 Write property test for 2FA login flow
    - **Property 7: 2FA Login Flow**
    - **Validates: Requirements 3.2, 3.4**
  
  - [x] 8.4 Write property test for invalid TOTP rejection
    - **Property 8: Invalid TOTP Rejection**
    - **Validates: Requirements 3.3**
  
  - [x] 8.5 Write property test for 2FA toggle security
    - **Property 9: 2FA Toggle Security**
    - **Validates: Requirements 3.6**
  
  - [x] 8.6 Write property test for backup code generation
    - **Property 10: Backup Code Generation**
    - **Validates: Requirements 3.7**
  
  - [x] 8.7 Write unit tests for 2FA functionality
    - Test TOTP validation with time drift
    - Test backup code consumption
    - Test QR code provisioning URI format
    - _Requirements: 3.1-3.7_

- [x] 9. Implement Session Manager component
  - [x] 9.1 Create SessionManager class
    - Implement create_session() method
    - Implement update_activity() method
    - Implement is_expired() method
    - Implement invalidate_session() method
    - Implement get_remaining_time() method
    - Create before_request handler for timeout checking
    - Load configuration from environment variables
    - _Requirements: 4.1-4.5_
  
  - [x] 9.2 Write property test for session expiration time
    - **Property 11: Session Expiration Time**
    - **Validates: Requirements 4.1**
  
  - [x] 9.3 Write property test for session activity tracking
    - **Property 12: Session Activity Tracking**
    - **Validates: Requirements 4.2**
  
  - [x] 9.4 Write property test for session timeout enforcement
    - **Property 13: Session Timeout Enforcement**
    - **Validates: Requirements 4.3**
  
  - [x] 9.5 Write property test for logout session invalidation
    - **Property 14: Logout Session Invalidation**
    - **Validates: Requirements 4.5**
  
  - [x] 9.6 Write unit tests for session management
    - Test session creation with correct expiration
    - Test activity timestamp updates
    - Test session expiration at exact timeout
    - _Requirements: 4.1-4.5_

- [x] 10. Implement Security Headers and HTTPS Enforcement
  - [x] 10.1 Initialize Flask-Talisman with security headers
    - Configure Content-Security-Policy
    - Configure X-Frame-Options, X-Content-Type-Options, Referrer-Policy
    - Configure HSTS for HTTPS
    - Configure HTTPS enforcement based on environment
    - Load configuration from environment variables
    - _Requirements: 6.1-6.6, 7.1-7.4_
  
  - [x] 10.2 Write property test for security headers on all responses
    - **Property 16: Security Headers on All Responses**
    - **Validates: Requirements 6.6**
  
  - [x] 10.3 Write unit tests for security headers
    - Test each header is present with correct value
    - Test HSTS only in HTTPS mode
    - Test HTTPS redirect in production
    - Test HTTP allowed in development
    - _Requirements: 6.1-6.6, 7.1-7.4_

- [x] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Integrate security components with login flow
  - [x] 12.1 Update login route with security checks
    - Add rate limiting decorator
    - Check account lockout before authentication
    - Validate password complexity on password changes
    - Record login attempts (success and failure)
    - Update last_login_at on successful login
    - Reset failed attempts on successful login
    - Log account lockout events
    - _Requirements: 1.1, 2.1-2.4, 2.6, 8.7, 8.8_
  
  - [x] 12.2 Add 2FA verification step to login flow
    - Check if user has 2FA enabled after credential validation
    - Prompt for TOTP code if 2FA is enabled
    - Verify TOTP code before creating session
    - Handle invalid TOTP codes
    - Support backup code usage
    - _Requirements: 3.2-3.4_
  
  - [x] 12.3 Integrate session management with Flask-Login
    - Create session on successful login
    - Add before_request handler for session timeout checking
    - Update activity timestamp on each request
    - Invalidate session on logout
    - _Requirements: 4.1-4.5_
  
  - [x] 12.4 Write integration tests for complete login flow
    - Test login without 2FA
    - Test login with 2FA
    - Test login with account lockout
    - Test login with rate limiting
    - Test login with session timeout
    - _Requirements: 1.1, 2.1-2.4, 3.2-3.4, 4.1-4.5_
  
  - [x] 12.5 Write property test for backward compatibility
    - **Property 26: Backward Compatibility for Non-2FA Users**
    - **Validates: Requirements 12.1**

- [x] 13. Add 2FA management routes
  - [x] 13.1 Create route for 2FA setup
    - Generate TOTP secret
    - Display QR code for scanning
    - Verify initial TOTP code
    - Generate and display backup codes
    - Enable 2FA on successful verification
    - Log 2FA enable event
    - _Requirements: 3.1, 3.7, 8.10_
  
  - [x] 13.2 Create route for 2FA disable
    - Require current password
    - Require valid TOTP code
    - Disable 2FA on successful verification
    - Log 2FA disable event
    - _Requirements: 3.6, 8.10_
  
  - [x] 13.3 Create route for backup code regeneration
    - Require authentication
    - Generate new backup codes
    - Invalidate old backup codes
    - Display new codes
    - _Requirements: 3.7_
  
  - [x] 13.4 Write unit tests for 2FA management routes
    - Test complete 2FA enrollment flow
    - Test 2FA disable flow
    - Test backup code regeneration
    - _Requirements: 3.1, 3.6, 3.7_

- [x] 14. Update password change functionality
  - [x] 14.1 Add password validation to password change routes
    - Validate new password against complexity requirements
    - Return all validation errors if password is invalid
    - Update password only if validation passes
    - Log password change event
    - _Requirements: 5.1-5.7, 8.6_
  
  - [x] 14.2 Write unit tests for password change validation
    - Test password validation on change
    - Test error message completeness
    - Test successful password change
    - _Requirements: 5.1-5.7_

- [x] 15. Add audit logging to admin actions
  - [x] 15.1 Add audit logging to post CRUD operations
    - Log post creation with post ID
    - Log post updates with post ID
    - Log post deletion with post ID
    - Include user ID, username, IP address, timestamp
    - _Requirements: 8.1-8.3_
  
  - [x] 15.2 Add audit logging to media operations
    - Log media upload with file name
    - Log media deletion with file name
    - Include user ID, username, IP address, timestamp
    - _Requirements: 8.4, 8.5_
  
  - [x] 15.3 Add audit logging to settings changes
    - Log settings changes with changed fields
    - Include user ID, username, IP address, timestamp
    - _Requirements: 8.6_
  
  - [x] 15.4 Write unit tests for admin action logging
    - Test each action type creates correct log entry
    - Test log entries contain all required fields
    - _Requirements: 8.1-8.6_

- [x] 16. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 17. Implement Security Dashboard
  - [x] 17.1 Create audit logs page
    - Display audit logs in reverse chronological order
    - Show timestamp, user, action type, details for each entry
    - Implement pagination (50 entries per page)
    - Add filtering by date range, user, action type
    - Restrict access to admin users only
    - _Requirements: 9.1-9.4_
  
  - [x] 17.2 Create login attempts page
    - Display recent login attempts
    - Show timestamp, username, IP address, success/failure status
    - Implement pagination (50 entries per page)
    - Add filtering by date range, username, success status
    - Restrict access to admin users only
    - _Requirements: 9.5, 9.6_
  
  - [x] 17.3 Add export functionality
    - Create route for exporting logs as CSV
    - Include all fields in export
    - Apply current filters to export
    - Restrict access to admin users only
    - _Requirements: 9.1-9.6_
  
  - [x] 17.4 Write property test for audit log chronological ordering
    - **Property 20: Audit Log Chronological Ordering**
    - **Validates: Requirements 9.1**
  
  - [x] 17.5 Write property test for audit log display completeness
    - **Property 21: Audit Log Display Completeness**
    - **Validates: Requirements 9.2**
  
  - [x] 17.6 Write property test for audit log pagination
    - **Property 22: Audit Log Pagination**
    - **Validates: Requirements 9.3**
  
  - [x] 17.7 Write property test for audit log filtering
    - **Property 23: Audit Log Filtering**
    - **Validates: Requirements 9.4**
  
  - [x] 17.8 Write property test for login attempt display completeness
    - **Property 24: Login Attempt Display Completeness**
    - **Validates: Requirements 9.6**
  
  - [x] 17.9 Write unit tests for security dashboard
    - Test audit log page rendering
    - Test login attempts page rendering
    - Test pagination controls
    - Test filtering UI
    - Test export functionality
    - Test admin-only access
    - _Requirements: 9.1-9.6_

- [x] 18. Implement error handling and user feedback
  - [x] 18.1 Create custom error classes
    - Create SecurityError base class
    - Create RateLimitExceeded error
    - Create AccountLocked error
    - Create InvalidTOTP error
    - Create SessionExpired error
    - Create PasswordValidationError error
    - _Requirements: 13.1-13.6_
  
  - [x] 18.2 Add error handlers to Flask app
    - Register error handler for SecurityError
    - Return appropriate HTTP status codes
    - Include retry-after header for rate limit errors
    - Format error messages according to requirements
    - _Requirements: 13.1-13.6_
  
  - [x] 18.3 Update routes to use custom errors
    - Replace generic exceptions with custom errors
    - Ensure error messages match requirements
    - Test error handling in all security flows
    - _Requirements: 13.1-13.6_
  
  - [x] 18.4 Write unit tests for error handling
    - Test each error type returns correct status code
    - Test error messages match requirements
    - Test retry-after header on rate limit
    - Test error logging
    - _Requirements: 13.1-13.6_

- [x] 19. Update environment configuration
  - [x] 19.1 Add security configuration to .env.example
    - Document all security-related environment variables
    - Provide sensible defaults
    - Include comments explaining each variable
    - _Requirements: 11.1-11.8_
  
  - [x] 19.2 Update configuration loading
    - Load all security settings from environment
    - Provide fallback defaults
    - Validate configuration values
    - _Requirements: 11.1-11.8_
  
  - [x] 19.3 Write unit tests for configuration loading
    - Test each environment variable is loaded correctly
    - Test default values are used when not set
    - Test configuration validation
    - _Requirements: 11.1-11.8_

- [x] 20. Update documentation
  - [x] 20.1 Update README with security features
    - Document rate limiting configuration
    - Document account lockout configuration
    - Document 2FA setup process
    - Document session timeout configuration
    - Document password requirements
    - Document security headers
    - Document HTTPS enforcement
    - Document audit logging
    - _Requirements: 1.1-13.6_
  
  - [x] 20.2 Create security configuration guide
    - Document all environment variables
    - Provide production deployment recommendations
    - Document security best practices
    - Include troubleshooting section
    - _Requirements: 11.1-11.8_
  
  - [x] 20.3 Update PRODUCTION_SETUP.md
    - Add security hardening checklist
    - Document HTTPS setup requirements
    - Document Redis setup for rate limiting (optional)
    - Document security monitoring recommendations
    - _Requirements: 1.1-7.4_

- [x] 21. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 22. Verify backward compatibility
  - [x] 22.1 Run existing test suite
    - Ensure all existing tests still pass
    - Verify no breaking changes to existing functionality
    - _Requirements: 12.1-12.5_
  
  - [x] 22.2 Test existing authentication flow
    - Test login without 2FA works as before
    - Test existing routes are accessible
    - Test CSRF protection still works
    - Test password hashing still works
    - _Requirements: 12.1-12.5_
  
  - [x] 22.3 Write integration tests for backward compatibility
    - Test complete authentication flow for non-2FA users
    - Test existing user data is preserved
    - Test existing routes maintain URL structure
    - _Requirements: 12.1-12.5_

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties with minimum 100 iterations
- Unit tests validate specific examples, edge cases, and error conditions
- Integration tests validate end-to-end flows across multiple components
- All security components are configurable via environment variables
- Backward compatibility is maintained throughout implementation
- All tasks are required for comprehensive security coverage

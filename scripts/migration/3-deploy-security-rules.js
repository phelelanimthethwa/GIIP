#!/usr/bin/env node
/**
 * Phase A - Step 3: Deploy Multi-Conference Security Rules
 * This script creates and deploys the new security rules for multi-conference support
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

console.log('=== GIIR Conference System - Security Rules Deployment ===');
console.log('Phase A - Step 3: Deploy Multi-Conference Security Rules');
console.log('');

// New multi-conference security rules
const newSecurityRules = {
  "rules": {
    // Global settings - admin only
    "global_settings": {
      ".read": "auth != null",
      ".write": "auth != null && root.child('users').child(auth.uid).child('is_global_admin').val() === true"
    },
    
    // Conferences collection
    "conferences": {
      ".read": "auth != null",
      "$conference_id": {
        ".write": "auth != null && (root.child('users').child(auth.uid).child('is_global_admin').val() === true || root.child('conference_admins').child($conference_id).child(auth.uid).child('permission_level').val() === 'admin')",
        "basic_info": {
          ".read": true  // Public conference info
        },
        ".indexOn": ["basic_info/status", "basic_info/year", "basic_info/start_date"]
      }
    },
    
    // Conference-specific registrations
    "conference_registrations": {
      "$conference_id": {
        "registrations": {
          ".indexOn": ["user_id", "email", "registration_type", "payment_status", "registration_date"],
          "$registration_id": {
            ".read": "auth != null && (data.child('user_id').val() === auth.uid || root.child('users').child(auth.uid).child('is_global_admin').val() === true || root.child('conference_admins').child($conference_id).child(auth.uid).exists())",
            ".write": "auth != null && (newData.child('user_id').val() === auth.uid || root.child('users').child(auth.uid).child('is_global_admin').val() === true || root.child('conference_admins').child($conference_id).child(auth.uid).child('permission_level').val() === 'admin')"
          }
        }
      }
    },
    
    // Conference-specific papers
    "conference_papers": {
      "$conference_id": {
        "papers": {
          ".indexOn": ["user_id", "email", "status", "submission_date"],
          "$paper_id": {
            ".read": "auth != null && (data.child('user_id').val() === auth.uid || root.child('users').child(auth.uid).child('is_global_admin').val() === true || root.child('conference_admins').child($conference_id).child(auth.uid).exists())",
            ".write": "auth != null && (newData.child('user_id').val() === auth.uid || root.child('users').child(auth.uid).child('is_global_admin').val() === true || root.child('conference_admins').child($conference_id).child(auth.uid).child('permission_level').val() === 'admin')"
          }
        }
      }
    },
    
    // Conference schedule
    "conference_schedule": {
      "$conference_id": {
        "sessions": {
          ".read": "auth != null",
          ".write": "auth != null && (root.child('users').child(auth.uid).child('is_global_admin').val() === true || root.child('conference_admins').child($conference_id).child(auth.uid).child('permission_level').val() === 'admin')"
        }
      }
    },
    
    // Conference announcements
    "conference_announcements": {
      "$conference_id": {
        "announcements": {
          ".read": "auth != null",
          ".write": "auth != null && (root.child('users').child(auth.uid).child('is_global_admin').val() === true || root.child('conference_admins').child($conference_id).child(auth.uid).child('permission_level').val() === 'admin')"
        }
      }
    },
    
    // Conference speakers
    "conference_speakers": {
      "$conference_id": {
        "speakers": {
          ".read": true,  // Public speaker info
          ".write": "auth != null && (root.child('users').child(auth.uid).child('is_global_admin').val() === true || root.child('conference_admins').child($conference_id).child(auth.uid).child('permission_level').val() === 'admin')"
        }
      }
    },
    
    // Conference downloads
    "conference_downloads": {
      "$conference_id": {
        "downloads": {
          ".read": true,  // Public downloads
          ".write": "auth != null && (root.child('users').child(auth.uid).child('is_global_admin').val() === true || root.child('conference_admins').child($conference_id).child(auth.uid).child('permission_level').val() === 'admin')",
          ".indexOn": ["category", "type"]
        }
      }
    },
    
    // Users collection - updated for global admin support
    "users": {
      ".indexOn": ["email", "is_global_admin"],
      "$uid": {
        ".read": "auth != null && (auth.uid === $uid || root.child('users').child(auth.uid).child('is_global_admin').val() === true)",
        ".write": "auth != null && (auth.uid === $uid || root.child('users').child(auth.uid).child('is_global_admin').val() === true)"
      }
    },
    
    // User-conference associations
    "user_conferences": {
      "$user_id": {
        ".read": "auth != null && (auth.uid === $user_id || root.child('users').child(auth.uid).child('is_global_admin').val() === true)",
        ".write": "auth != null && auth.uid === $user_id",
        ".indexOn": ["last_activity"],
        "$conference_id": {
          ".validate": "root.child('conferences').child($conference_id).exists()"
        }
      }
    },
    
    // Conference admins
    "conference_admins": {
      "$conference_id": {
        ".read": "auth != null && (root.child('users').child(auth.uid).child('is_global_admin').val() === true || root.child('conference_admins').child($conference_id).child(auth.uid).exists())",
        ".indexOn": ["permission_level", "granted_at"],
        "$admin_user_id": {
          ".write": "auth != null && (root.child('users').child(auth.uid).child('is_global_admin').val() === true || (root.child('conference_admins').child($conference_id).child(auth.uid).child('permission_level').val() === 'admin' && newData.child('permission_level').val() !== 'admin'))",
          ".validate": "newData.hasChildren(['permission_level', 'granted_by', 'granted_at'])"
        }
      }
    },
    
    // Payment proofs - updated for conference-specific structure
    "payment_proofs": {
      "$user_id": {
        ".read": "auth != null && (auth.uid === $user_id || root.child('users').child(auth.uid).child('is_global_admin').val() === true)",
        ".write": "auth != null && (auth.uid === $user_id || root.child('users').child(auth.uid).child('is_global_admin').val() === true)",
        "$conference_id": {
          "$proof_id": {
            ".validate": "newData.hasChildren(['filename', 'original_filename', 'file_size', 'upload_date', 'status', 'mime_type'])"
          }
        }
      }
    },
    
    // Legacy collections - maintain during transition period
    "registrations": {
      ".read": "auth != null",
      ".write": false,  // Read-only during migration
      ".indexOn": ["email", "user_id", "registration_type", "registration_period", "payment_status"],
      "$registration_id": {
        ".read": "auth != null && (data.child('email').val() === auth.token.email || root.child('users').child(auth.uid).child('is_global_admin').val() === true)"
      }
    },
    
    "papers": {
      ".read": "auth != null",
      ".write": false,  // Read-only during migration
      ".indexOn": ["email", "status"],
      "$paper_id": {
        ".read": "auth != null && (data.child('email').val() === auth.token.email || root.child('users').child(auth.uid).child('is_global_admin').val() === true)"
      }
    },
    
    // Global collections that remain unchanged
    "contact_submissions": {
      ".read": "auth != null && root.child('users').child(auth.uid).child('is_global_admin').val() === true",
      ".write": true,
      ".indexOn": ["email", "submitted_at"]
    },
    
    "email_settings": {
      ".read": "auth != null && root.child('users').child(auth.uid).child('is_global_admin').val() === true",
      ".write": "auth != null && root.child('users').child(auth.uid).child('is_global_admin').val() === true"
    },
    
    "contact_email_settings": {
      ".read": "auth != null && root.child('users').child(auth.uid).child('is_global_admin').val() === true",
      ".write": "auth != null && root.child('users').child(auth.uid).child('is_global_admin').val() === true"
    },
    
    "contact_page_settings": {
      ".read": true,
      ".write": "auth != null && root.child('users').child(auth.uid).child('is_global_admin').val() === true"
    }
  }
};

async function backupCurrentRules() {
  try {
    console.log('📋 Backing up current security rules...');
    
    const backupDir = path.join(__dirname, '../../backups');
    if (!fs.existsSync(backupDir)) {
      fs.mkdirSync(backupDir, { recursive: true });
    }
    
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupFile = path.join(backupDir, `database-rules-backup-${timestamp}.json`);
    
    // Read current rules
    const currentRulesPath = path.join(__dirname, '../../database.rules.json');
    if (fs.existsSync(currentRulesPath)) {
      const currentRules = fs.readFileSync(currentRulesPath, 'utf8');
      fs.writeFileSync(backupFile, currentRules);
      console.log(`✅ Current rules backed up to: ${backupFile}`);
    } else {
      console.log('⚠️  No existing rules file found');
    }
    
    return backupFile;
  } catch (error) {
    console.error('❌ Error backing up rules:', error);
    throw error;
  }
}

async function deployNewRules() {
  try {
    console.log('📝 Creating new security rules file...');
    
    const rulesPath = path.join(__dirname, '../../database.rules.json');
    fs.writeFileSync(rulesPath, JSON.stringify(newSecurityRules, null, 2));
    console.log('✅ New rules file created');
    
    console.log('🚀 Deploying rules to Firebase...');
    
    // Deploy the rules
    execSync('firebase deploy --only database', { 
      stdio: 'inherit',
      cwd: path.join(__dirname, '../..')
    });
    
    console.log('✅ Security rules deployed successfully');
    
  } catch (error) {
    console.error('❌ Error deploying rules:', error);
    throw error;
  }
}

async function validateRulesDeployment() {
  try {
    console.log('🔍 Validating rules deployment...');
    
    // Test basic rule functionality
    execSync('firebase database:test --rules database.rules.json', {
      cwd: path.join(__dirname, '../..'),
      stdio: 'pipe'
    });
    
    console.log('✅ Security rules validation passed');
    return true;
    
  } catch (error) {
    console.error('❌ Rules validation failed:', error.message);
    return false;
  }
}

async function main() {
  try {
    console.log('🔐 Starting security rules deployment...');
    console.log('');
    
    // Step 1: Backup current rules
    const backupFile = await backupCurrentRules();
    
    // Step 2: Deploy new rules
    await deployNewRules();
    
    // Step 3: Validate deployment
    const validated = await validateRulesDeployment();
    
    if (validated) {
      console.log('');
      console.log('=== Security Rules Deployment Complete ===');
      console.log('✅ Multi-conference security rules deployed successfully');
      console.log('✅ Conference isolation enabled');
      console.log('✅ Role-based access control implemented');
      console.log('');
      console.log('🔍 New Features:');
      console.log('  • Conference-specific admin permissions');
      console.log('  • Global admin vs conference admin roles');
      console.log('  • User-conference association controls');
      console.log('  • Conference data isolation');
      console.log('');
      console.log('📁 Backup created:', backupFile);
      console.log('');
      console.log('🎉 Phase A completed successfully!');
      console.log('Next: Begin Phase B - Data Migration');
      console.log('Run: node 4-migrate-users.js');
      
      process.exit(0);
    } else {
      throw new Error('Rules validation failed');
    }
    
  } catch (error) {
    console.error('❌ Security rules deployment failed:', error);
    console.error('');
    console.error('🔄 To rollback:');
    console.error('1. Restore backup rules file');
    console.error('2. Run: firebase deploy --only database');
    process.exit(1);
  }
}

// Run the deployment
main(); 
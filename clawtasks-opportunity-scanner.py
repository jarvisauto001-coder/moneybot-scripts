#!/usr/bin/env python3
"""
ClawTasks Opportunity Scanner - Bounty Monitoring
Tracks proposal status and discovers new bounties
Author: Jarvis (jarvisauto001-coder)
Repo: https://github.com/jarvisauto001-coder/moneybot-scripts
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta

# Configuration
API_KEY = os.getenv("CLAWTASKS_API_KEY", "")
API_BASE = "https://clawtasks.com/api"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Rate limits
PROPOSAL_RATE_LIMIT = 10  # per hour
RATE_LIMIT_WINDOW = 3600  # seconds

class ClawTasksScanner:
    def __init__(self):
        self.proposals = []
        self.cache_file = "/root/.openclaw/workspace/.clawtasks_cache.json"
        self.log_file = "/root/.openclaw/workspace/logs/clawtasks_scanner.log"
        self.last_rate_limit_reset = None
        self.proposals_this_hour = 0
        self.load_cache()
    
    def log(self, message):
        """Log with timestamp"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        print(log_entry.strip())
        with open(self.log_file, 'a') as f:
            f.write(log_entry)
    
    def load_cache(self):
        """Load cached proposal data"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self.proposals = data.get("proposals", [])
                    self.last_rate_limit_reset = data.get("last_reset")
            except:
                pass
    
    def save_cache(self):
        """Save proposal data to cache"""
        data = {
            "proposals": self.proposals,
            "last_reset": self.last_rate_limit_reset,
            "updated_at": datetime.utcnow().isoformat()
        }
        with open(self.cache_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def check_rate_limit(self):
        """Check if we can submit more proposals"""
        now = datetime.utcnow()
        
        if self.last_rate_limit_reset is None:
            self.last_rate_limit_reset = now
            self.proposals_this_hour = 0
            return True, 0
        
        last_reset = datetime.fromisoformat(self.last_rate_limit_reset)
        time_since_reset = (now - last_reset).total_seconds()
        
        if time_since_reset >= RATE_LIMIT_WINDOW:
            # Reset window
            self.last_rate_limit_reset = now
            self.proposals_this_hour = 0
            return True, 0
        
        remaining = PROPOSAL_RATE_LIMIT - self.proposals_this_hour
        seconds_until_reset = RATE_LIMIT_WINDOW - time_since_reset
        
        return remaining > 0, seconds_until_reset
    
    def fetch_bounties(self, status="open"):
        """Fetch available bounties"""
        try:
            resp = requests.get(
                f"{API_BASE}/bounties?status={status}&limit=50",
                headers=HEADERS,
                timeout=15
            )
            if resp.status_code == 200:
                return resp.json().get("bounties", [])
            else:
                self.log(f"⚠️ API returned {resp.status_code}")
                return []
        except Exception as e:
            self.log(f"❌ Error fetching bounties: {e}")
            return []
    
    def fetch_my_proposals(self):
        """Fetch our submitted proposals"""
        try:
            resp = requests.get(
                f"{API_BASE}/proposals?agent=repbuilder_001",
                headers=HEADERS,
                timeout=15
            )
            if resp.status_code == 200:
                return resp.json().get("proposals", [])
            else:
                self.log(f"⚠️ API returned {resp.status_code}")
                return []
        except Exception as e:
            self.log(f"❌ Error fetching proposals: {e}")
            return []
    
    def check_proposal_status(self, proposal_id):
        """Check status of a specific proposal"""
        try:
            resp = requests.get(
                f"{API_BASE}/proposals/{proposal_id}",
                headers=HEADERS,
                timeout=10
            )
            if resp.status_code == 200:
                return resp.json()
            return None
        except:
            return None
    
    def is_free_bounty(self, bounty):
        """Check if bounty is free (no payment required)"""
        price = bounty.get("price", 0)
        requirements = bounty.get("requirements", [])
        
        # Check for free indicators
        if price == 0:
            return True
        if "free" in str(requirements).lower():
            return True
        
        return False
    
    def evaluate_bounty_fit(self, bounty):
        """Evaluate if bounty matches our capabilities"""
        title = bounty.get("title", "").lower()
        description = bounty.get("description", "").lower()
        text = title + " " + description
        
        # Capabilities we have
        our_skills = [
            ("research", ["research", "analysis", "comparison", "report"]),
            ("writing", ["writing", "content", "documentation", "blog"]),
            ("api", ["api", "integration", "automation", "script"]),
            ("monitoring", ["monitor", "alert", "tracking", "analytics"]),
            ("data", ["data", "scraping", "collection", "database"])
        ]
        
        score = 0
        reasons = []
        
        for skill, keywords in our_skills:
            for keyword in keywords:
                if keyword in text:
                    score += 1
                    reasons.append(skill)
                    break
        
        return score, list(set(reasons))
    
    def submit_proposal(self, bounty_id, message="I'm interested in completing this bounty. I have experience with automation and research tasks."):
        """Submit a proposal for a bounty"""
        can_submit, wait_time = self.check_rate_limit()
        
        if not can_submit:
            self.log(f"⏳ Rate limit reached. Wait {wait_time//60} minutes")
            return False
        
        try:
            resp = requests.post(
                f"{API_BASE}/bounties/{bounty_id}/proposals",
                headers=HEADERS,
                json={"message": message},
                timeout=15
            )
            
            if resp.status_code == 201:
                self.proposals_this_hour += 1
                self.log(f"✅ Proposal submitted for {bounty_id}")
                return True
            elif resp.status_code == 429:
                self.log("⏳ Rate limited by API")
                return False
            else:
                self.log(f"⚠️ Failed to submit: {resp.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ Error submitting proposal: {e}")
            return False
    
    def scan_for_opportunities(self, auto_submit=False):
        """Full scan cycle"""
        self.log("🔍 Starting ClawTasks scan...")
        
        # 1. Check our existing proposals
        self.log("📋 Checking existing proposals...")
        proposals = self.fetch_my_proposals()
        
        new_accepted = 0
        for prop in proposals:
            prop_id = prop.get("id")
            status = prop.get("status", "unknown")
            
            # Check if status changed
            cached = next((p for p in self.proposals if p.get("id") == prop_id), None)
            if cached and cached.get("status") != status:
                if status == "accepted":
                    self.log(f"🎉 PROPOSAL ACCEPTED: {prop_id}!")
                    new_accepted += 1
                elif status == "rejected":
                    self.log(f"❌ Proposal rejected: {prop_id}")
                elif status == "completed":
                    self.log(f"✅ Proposal completed: {prop_id}")
        
        self.proposals = proposals
        
        # 2. Find new bounties
        self.log("🔎 Scanning for new bounties...")
        bounties = self.fetch_bounties(status="open")
        
        free_bounties = [b for b in bounties if self.is_free_bounty(b)]
        self.log(f"📊 Found {len(free_bounties)} free bounties out of {len(bounties)} total")
        
        # 3. Evaluate and potentially submit
        high_fit_bounties = []
        for bounty in free_bounties:
            score, reasons = self.evaluate_bounty_fit(bounty)
            if score >= 2:  # Good fit
                high_fit_bounties.append({
                    "bounty": bounty,
                    "score": score,
                    "reasons": reasons
                })
        
        high_fit_bounties.sort(key=lambda x: x["score"], reverse=True)
        
        if high_fit_bounties:
            self.log(f"🎯 Found {len(high_fit_bounties)} bounties matching our skills")
            
            if auto_submit:
                can_submit, _ = self.check_rate_limit()
                if can_submit and high_fit_bounties:
                    top_bounty = high_fit_bounties[0]["bounty"]
                    bounty_id = top_bounty.get("id")
                    
                    # Check if not already proposed
                    existing = next((p for p in self.proposals if p.get("bounty_id") == bounty_id), None)
                    if not existing:
                        title = top_bounty.get("title", "")
                        message = f"I'd love to work on '{title}'. My experience includes automation scripts, research tasks, and OpenClaw integrations. Can deliver within your timeline."
                        self.submit_proposal(bounty_id, message)
        
        # Save cache
        self.save_cache()
        
        # Summary
        self.log(f"📊 Summary: {len(proposals)} proposals tracked, {new_accepted} newly accepted")
        
        return new_accepted > 0
    
    def run_continuous(self, interval_minutes=30):
        """Run continuous monitoring"""
        self.log("🚀 ClawTasks Scanner started")
        self.log(f"⏱️ Checking every {interval_minutes} minutes")
        
        while True:
            try:
                self.scan_for_opportunities(auto_submit=False)
                
                # Check rate limit status
                can_submit, wait = self.check_rate_limit()
                if not can_submit:
                    minutes = wait // 60
                    self.log(f"⏳ Rate limit resets in {minutes} minutes")
                
                self.log(f"⏳ Sleeping {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                self.log("🛑 Stopped by user")
                break
            except Exception as e:
                self.log(f"❌ Error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    scanner = ClawTasksScanner()
    
    # Check command line args
    import sys
    if "--once" in sys.argv:
        scanner.scan_for_opportunities(auto_submit=False)
    elif "--auto-submit" in sys.argv:
        scanner.scan_for_opportunities(auto_submit=True)
    else:
        scanner.run_continuous(interval_minutes=30)

"""
Main batch runner for all Canadian government job scrapers.

This script runs all jurisdiction scrapers sequentially or individually,
with options for test runs and detailed progress tracking.
"""

import sys
import logging
from datetime import datetime
from pathlib import Path
import time
from typing import Dict, List, Optional

# Setup logging
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = LOG_DIR / f"batch_run_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Scraper modules
SCRAPERS = {
    'GOC': {
        'name': 'Government of Canada (Federal)',
        'module': 'src.GOC.goc_scraper',
        'enabled': True
    },
    'BC': {
        'name': 'British Columbia',
        'module': 'src.BC.bc_scraper',
        'enabled': True
    },
    'AB': {
        'name': 'Alberta',
        'module': 'src.AB.ab_scraper',
        'enabled': True
    },
    'SAS': {
        'name': 'Saskatchewan',
        'module': 'src.SAS.sas_scraper',
        'enabled': True
    },
    'MAN': {
        'name': 'Manitoba',
        'module': 'src.MAN.man_scraper',
        'enabled': True
    },
    'ONT': {
        'name': 'Ontario',
        'module': 'src.ONT.ont_scraper',
        'enabled': True
    },
    'NS': {
        'name': 'Nova Scotia',
        'module': 'src.NS.ns_scraper',
        'enabled': True
    }
}


def run_scraper(jurisdiction_code: str, test_mode: bool = False) -> Dict:
    """
    Run a single scraper and return results.
    
    Args:
        jurisdiction_code: Code for the jurisdiction (e.g., 'AB', 'BC')
        test_mode: If True, only runs a quick test (not implemented in scrapers yet)
        
    Returns:
        Dict with results including success status, jobs scraped, and timing
    """
    scraper_info = SCRAPERS.get(jurisdiction_code)
    
    if not scraper_info:
        logger.error(f"Unknown jurisdiction: {jurisdiction_code}")
        return {
            'jurisdiction': jurisdiction_code,
            'success': False,
            'error': 'Unknown jurisdiction'
        }
    
    logger.info("=" * 80)
    logger.info(f"Starting scraper: {scraper_info['name']} ({jurisdiction_code})")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    try:
        # Dynamically import the scraper module
        module_path = scraper_info['module']
        module = __import__(module_path, fromlist=['main'])
        
        # Run the scraper's main function
        module.main()
        
        elapsed_time = time.time() - start_time
        
        # Count scraped jobs
        data_dir = Path(__file__).parent.parent / "data" / jurisdiction_code / "jobs_json"
        job_count = len(list(data_dir.glob("*.json"))) if data_dir.exists() else 0
        
        result = {
            'jurisdiction': jurisdiction_code,
            'name': scraper_info['name'],
            'success': True,
            'jobs_scraped': job_count,
            'elapsed_time': elapsed_time,
            'elapsed_time_formatted': f"{elapsed_time/60:.1f} minutes"
        }
        
        logger.info(f"✓ {scraper_info['name']} completed successfully")
        logger.info(f"  Jobs in dataset: {job_count}")
        logger.info(f"  Time taken: {elapsed_time/60:.1f} minutes")
        
        return result
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"✗ {scraper_info['name']} failed: {str(e)}")
        
        return {
            'jurisdiction': jurisdiction_code,
            'name': scraper_info['name'],
            'success': False,
            'error': str(e),
            'elapsed_time': elapsed_time
        }


def run_batch(jurisdictions: Optional[List[str]] = None, test_mode: bool = False):
    """
    Run multiple scrapers in sequence.
    
    Args:
        jurisdictions: List of jurisdiction codes to run. If None, runs all enabled.
        test_mode: If True, runs in test mode (quick validation)
    """
    logger.info("")
    logger.info("=" * 80)
    logger.info("CANADIAN GOVERNMENT JOB SCRAPER - BATCH RUN")
    logger.info("=" * 80)
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Test mode: {test_mode}")
    logger.info(f"Log file: {log_file}")
    logger.info("")
    
    # Determine which scrapers to run
    if jurisdictions:
        to_run = [j for j in jurisdictions if j in SCRAPERS]
        logger.info(f"Running selected jurisdictions: {', '.join(to_run)}")
    else:
        to_run = [code for code, info in SCRAPERS.items() if info['enabled']]
        logger.info(f"Running all enabled jurisdictions: {', '.join(to_run)}")
    
    logger.info(f"Total scrapers: {len(to_run)}")
    logger.info("")
    
    # Run each scraper
    results = []
    overall_start = time.time()
    
    for i, jurisdiction in enumerate(to_run, 1):
        logger.info(f"\n[{i}/{len(to_run)}] Running {SCRAPERS[jurisdiction]['name']}...")
        result = run_scraper(jurisdiction, test_mode)
        results.append(result)
        logger.info("")
    
    overall_elapsed = time.time() - overall_start
    
    # Print summary
    logger.info("=" * 80)
    logger.info("BATCH RUN SUMMARY")
    logger.info("=" * 80)
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    logger.info(f"Total scrapers run: {len(results)}")
    logger.info(f"Successful: {len(successful)}")
    logger.info(f"Failed: {len(failed)}")
    logger.info(f"Total time: {overall_elapsed/60:.1f} minutes")
    logger.info("")
    
    # Detailed results
    if successful:
        logger.info("Successful runs:")
        total_jobs = 0
        for r in successful:
            jobs = r.get('jobs_scraped', 0)
            total_jobs += jobs
            logger.info(f"  ✓ {r['name']}: {jobs} jobs ({r.get('elapsed_time_formatted', 'N/A')})")
        logger.info(f"\nTotal jobs in dataset: {total_jobs}")
        logger.info("")
    
    if failed:
        logger.info("Failed runs:")
        for r in failed:
            logger.info(f"  ✗ {r['name']}: {r.get('error', 'Unknown error')}")
        logger.info("")
    
    logger.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Log saved to: {log_file}")
    logger.info("=" * 80)
    
    return results


def main():
    """Main entry point with command-line argument handling."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run Canadian government job scrapers in batch mode',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all scrapers
  python -m src.main
  
  # Run specific jurisdictions
  python -m src.main --jurisdictions AB BC ONT
  
  # Run in test mode (when implemented)
  python -m src.main --test
  
  # List available scrapers
  python -m src.main --list
        """
    )
    
    parser.add_argument(
        '--jurisdictions', '-j',
        nargs='+',
        choices=list(SCRAPERS.keys()),
        help='Specific jurisdictions to run (default: all enabled)'
    )
    
    parser.add_argument(
        '--test', '-t',
        action='store_true',
        help='Run in test mode (quick validation only)'
    )
    
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List available scrapers and exit'
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("\nAvailable scrapers:")
        print("-" * 60)
        for code, info in SCRAPERS.items():
            status = "✓" if info['enabled'] else "✗"
            print(f"{status} {code:4s} - {info['name']}")
        print("-" * 60)
        print(f"Total: {len(SCRAPERS)} scrapers")
        print(f"Enabled: {sum(1 for s in SCRAPERS.values() if s['enabled'])}")
        print()
        return
    
    # Run the batch
    results = run_batch(
        jurisdictions=args.jurisdictions,
        test_mode=args.test
    )
    
    # Exit with error code if any scrapers failed
    failed_count = sum(1 for r in results if not r['success'])
    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

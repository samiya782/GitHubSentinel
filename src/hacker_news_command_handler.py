import argparse
from typing import Type
from hacker_news_client import HackerNewsClient
from report_generator import ReportGenerator  # Assuming you have a ReportGenerator class for generating reports

class HackerNewsCommandHandler:
    """
    Handles command-line operations for the Hacker News client.
    It uses a sub-parser system to manage different commands like 'export' and 'show'.
    """

    def __init__(self, hacker_news_client: HackerNewsClient | Type[HackerNewsClient], report_generator: ReportGenerator):
        self.client = hacker_news_client
        self.parser = self.create_parser()
        self.report_generator = report_generator

    def create_parser(self):
        parser = argparse.ArgumentParser(
            description='Hacker News Command Line Interface',
            formatter_class=argparse.RawTextHelpFormatter,
            add_help=False  # We will create our own help command
        )
        subparsers = parser.add_subparsers(title='Commands', dest='command')

        # --- Export Command ---
        parser_export = subparsers.add_parser('export', help='Fetch and export stories to a file.')
        parser_export.add_argument('-p', '--pages', type=int, default=1, help='Number of pages to scrape (default: 1)')
        parser_export.set_defaults(func=self.handle_export)

        # --- Show Command ---
        parser_show = subparsers.add_parser('show', help='Show top stories in the console without saving.')
        parser_show.add_argument('-p', '--pages', type=int, default=1, help='Number of pages to show (default: 1)')
        parser_show.set_defaults(func=self.handle_show)

        # --- Generate Command ---
        parser_generate = subparsers.add_parser('generate', help='Generate report from markdown file')
        parser_generate.add_argument('file', type=str, help='The markdown file to generate report from')
        parser_generate.set_defaults(func=self.generate_daily_report)

        # --- Help Command ---
        parser_help = subparsers.add_parser('help', help='Show this help message.')
        parser_help.set_defaults(func=self.print_help)

        return parser

    def handle_export(self, args):
        print(f"Exporting stories from {args.pages} page(s)...")
        self.client.export_daily_news(page=args.pages)

    def handle_show(self, args):
        print(f"Showing top stories from {args.pages} page(s):\n")
        stories = self.client.fetch_hackernews_top_stories(page=args.pages)
        if not stories:
            print("Could not retrieve any stories.")
            return

        for idx, story in enumerate(stories, start=1):
            print(f"{idx}. {story['title']}")
            print(f"   Link: {story['link']}\n")

    def generate_daily_report(self, args):
        self.report_generator.generate_daily_report(args.file)
        print(f"Generated daily report from file: {args.file}")

    def print_help(self, args = None):
        """Handler for the 'help' command."""
        self.parser.print_help(args)

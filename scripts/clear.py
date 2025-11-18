# -*- coding: utf-8 -*-
"""
Created on Tue Nov 18 02:17:34 2025

@author: jelte
"""

def delete_generated_events():
        """Deletes all events previously created by this script."""
        print(f"--- CLEANUP: Deleting existing generated events for {self.today_date_str} ---")
        try:
            start_of_day = datetime.datetime.strptime(self.today_date_str, "%Y-%m-%d")
            end_of_window = start_of_day + datetime.timedelta(days=2)
            time_min = start_of_day.isoformat() + 'Z'
            time_max = end_of_window.isoformat() + 'Z'

            events_result = self.services["calendar"].events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                privateExtendedProperty=f'sourceId={GENERATOR_ID}'
            ).execute()
            
            events_to_delete = events_result.get('items', [])
            if not events_to_delete:
                print("INFO: No previous AI-generated events found to delete.")
                return

            print(f"INFO: Found {len(events_to_delete)} previously generated events to delete...")
            batch = self.services["calendar"].new_batch_http_request()
            deleted_count = 0

            def callback(request_id, response, exception):
                nonlocal deleted_count
                if exception is None:
                    deleted_count += 1
            
            for event in events_to_delete:
                batch.add(
                    self.services["calendar"].events().delete(
                        calendarId='primary', eventId=event['id']
                    ),
                    callback=callback
                )
            batch.execute()
            print(f"SUCCESSFULLY DELETED {deleted_count} PREVIOUSLY GENERATED EVENTS.")
        except Exception as e:
            print(f"ERROR deleting events: {e}")
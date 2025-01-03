import requests
import json
from datetime import datetime
import time
from typing import Dict, List, Optional
import sys
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich import print as rprint

class SwedenWeatherUI:
    def __init__(self):
        self.base_url = "https://opendata-download-metobs.smhi.se/api"
        self.console = Console()
        self.favorites = {}  # Initialize empty favorites dictionary
        
        # Initialize parameters (existing code)
        self.parameters = {
            "1": {
                "name": "Lufttemperatur momentanvärde, 1 gång/tim",
                "id": "2",
                "unit": "°C",
                "description": "Temperature"
            },
            "2": {
                "name": "Lufttryck reducerat havsytans nivå",
                "id": "9",
                "unit": "hPa",
                "description": "Air pressure"
            },
            "3": {
                "name": "Relativ Luftfuktighet momentanvärde, 1 gång/tim",
                "id": "6",
                "unit": "%",
                "description": "Relative humidity"
            },
            "4": {
                "name": "Nederbördsmängd summa 1 timme, 1 gång/tim",
                "id": "7",
                "unit": "mm",
                "description": "Precipitation amount"
            },
            "5": {
                "name": "Vindhastighet medelvärde 10 min, 1 gång/tim",
                "id": "4",
                "unit": "m/s",
                "description": "Wind speed"
            }
        }
        # Define available period types
        self.period_types = [
            "latest-hour",
            "latest-day",
            "latest-months"
        ]
        self.load_favorites()  # Load any saved favorites

    def save_favorites(self):
        """Save favorites to a file."""
        try:
            with open('weather_favorites.json', 'w') as f:
                json.dump(self.favorites, f)
        except Exception as e:
            self.console.print(f"[yellow]Could not save favorites: {e}[/yellow]")

    def load_favorites(self):
        """Load favorites from file."""
        try:
            with open('weather_favorites.json', 'r') as f:
                self.favorites = json.load(f)
        except FileNotFoundError:
            self.favorites = {}  # Start with empty favorites if file doesn't exist
        except Exception as e:
            self.console.print(f"[yellow]Could not load favorites: {e}[/yellow]")
            self.favorites = {}
        
    def fetch_data(self, url: str) -> Dict:
        """Fetch data from SMHI API."""
        try:
            self.console.print(f"[dim]Fetching URL: {url}[/dim]")
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            self.console.print("[dim]Data fetched successfully[/dim]")
            return data
        except requests.RequestException as e:
            self.console.print(f"[red]Error fetching data: {e}[/red]")
            raise

    def get_stations(self, parameter: str) -> List[Dict]:
        """Get available stations for a parameter."""
        try:
            url = f"{self.base_url}/version/latest/parameter/{parameter}.json"
            self.console.print("[dim]Fetching stations list...[/dim]")
            data = self.fetch_data(url)
            
            stations = []
            # Get basic station info from the main response
            for station in data.get("station", []):
                if station.get("active", False):  # Only include active stations
                    stations.append({
                        "key": station["key"],
                        "name": station["name"],
                        "active": station.get("active", False),
                        "height": station.get("height", 0),
                        "latitude": station.get("latitude", 0),
                        "longitude": station.get("longitude", 0)
                    })
            
            return sorted(stations, key=lambda x: x["name"])
            
        except Exception as e:
            self.console.print(f"[red]Error getting stations: {str(e)}[/red]")
            return []

    def get_available_periods(self, parameter: str, station_id: str) -> List[Dict]:
        """Get available periods for a station."""
        try:
            url = f"{self.base_url}/version/latest/parameter/{parameter}/station/{station_id}.json"
            data = self.fetch_data(url)
            periods = data.get("period", [])
            
            if not periods:
                self.console.print(f"[yellow]No data periods available for station {station_id} with this parameter.[/yellow]")
            
            # Get the most recent periods first
            return sorted(periods, key=lambda x: x["key"], reverse=True)
        except Exception as e:
            self.console.print(f"[red]Error getting periods: {str(e)}[/red]")
            return []

    def get_latest_weather(self, parameter: str, station_id: str) -> Optional[Dict]:
        """Get latest weather data for a station."""
        try:
            # First try latest-hour
            hour_url = f"{self.base_url}/version/latest/parameter/{parameter}/station/{station_id}/period/latest-hour/data.json"
            try:
                data = self.fetch_data(hour_url)
                if data.get("value") and len(data["value"]) > 0:
                    return data["value"][-1]  # Get most recent measurement
            except:
                self.console.print("[dim]No latest hour data available[/dim]")

            # Then try latest-day
            day_url = f"{self.base_url}/version/latest/parameter/{parameter}/station/{station_id}/period/latest-day/data.json"
            try:
                data = self.fetch_data(day_url)
                if data.get("value") and len(data["value"]) > 0:
                    return data["value"][-1]  # Get most recent measurement
            except:
                self.console.print("[dim]No latest day data available[/dim]")

            self.console.print("[yellow]No recent measurements available for this station.[/yellow]")
            return None

        except Exception as e:
            self.console.print(f"[red]Error getting weather data: {str(e)}[/red]")
            return None

    def display_parameters(self) -> Optional[str]:
        """Display available parameters and get user selection."""
        while True:
            table = Table(title="Available Weather Parameters")
            table.add_column("Option", justify="right", style="cyan")
            table.add_column("Parameter", style="green")
            table.add_column("Description", style="yellow")
            table.add_column("Unit", style="blue")
            
            for key, param_data in self.parameters.items():
                table.add_row(
                    key,
                    param_data["name"],
                    param_data["description"],
                    param_data["unit"]
                )
                
            self.console.print(table)
            
            choice = input("\nSelect a parameter (1-5) or 'q' to quit: ")
            if choice.lower() == 'q':
                return None
            if choice in self.parameters:
                return choice
            self.console.print("[red]Invalid choice. Please try again.[/red]")

    def display_stations(self, stations: List[Dict]) -> str:
        """Display available stations and get user selection."""
        if not stations:
            self.console.print("[red]No stations available for this parameter.[/red]")
            return None
            
        table = Table(title="Available Weather Stations")
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Active", style="yellow")
        table.add_column("Height (m)", justify="right", style="blue")
        table.add_column("Favorite", justify="center", style="magenta")
        
        # Show all active stations
        for station in stations:
            is_favorite = "★" if str(station["key"]) in self.favorites else ""
            table.add_row(
                str(station["key"]),
                station["name"],
                "Yes" if station["active"] else "No",
                str(round(station.get("height", 0), 1)),
                is_favorite
            )
            
        self.console.print(table)
        
        # First show favorites menu if there are any
        if self.favorites:
            self.console.print("\n[yellow]Favorite Stations:[/yellow]")
            for station_id, name in self.favorites.items():
                self.console.print(f"[magenta]★[/magenta] {station_id}: {name}")
        
        while True:
            station_id = input("\nEnter station ID (or 'f' to favorite/unfavorite, 'q' to go back): ").strip()
            
            if station_id.lower() == 'q':
                return None
                
            if station_id.lower() == 'f':
                fav_id = input("Enter station ID to toggle favorite status: ").strip()
                station = next((s for s in stations if str(s["key"]) == fav_id), None)
                if station:
                    if fav_id in self.favorites:
                        del self.favorites[fav_id]
                        self.console.print(f"[yellow]Removed {station['name']} from favorites[/yellow]")
                    else:
                        self.favorites[fav_id] = station["name"]
                        self.console.print(f"[green]Added {station['name']} to favorites[/green]")
                    self.save_favorites()
                    return self.display_stations(stations)  # Redraw the list
                else:
                    self.console.print("[red]Invalid station ID.[/red]")
                continue
                
            # Verify station exists
            station = next((s for s in stations if str(s["key"]) == station_id), None)
            if station is None:
                self.console.print("[red]Invalid station ID. Please try again.[/red]")
                continue
                
            if not station.get("active", False):
                self.console.print("[yellow]Warning: This station may be inactive.[/yellow]")
                if input("Do you want to try anyway? (y/n): ").lower() != 'y':
                    continue
                    
            return station_id

    def format_weather_data(self, data: Dict, parameter_choice: str) -> str:
        """Format weather data for display."""
        try:
            timestamp = datetime.fromtimestamp(data["date"] / 1000)  # Convert from milliseconds
            value = data["value"]
            
            # Convert value to float if it's a string
            try:
                value = float(value)
            except (ValueError, TypeError):
                # If conversion fails, return the raw value
                return f"{timestamp.strftime('%Y-%m-%d %H:%M')}: {value} {self.parameters[parameter_choice]['unit']}"
            
            # Format the value based on the type
            if self.parameters[parameter_choice]['unit'] in ["°C", "m/s", "mm"]:
                formatted_value = f"{value:.1f}"  # One decimal place for these units
            elif self.parameters[parameter_choice]['unit'] == "hPa":
                formatted_value = f"{value:.0f}"  # No decimals for pressure
            else:
                formatted_value = str(value)
                
            return f"{timestamp.strftime('%Y-%m-%d %H:%M')}: {formatted_value} {self.parameters[parameter_choice]['unit']}"
            
        except Exception as e:
            self.console.print(f"[red]Error formatting data: {str(e)}[/red]")
            # Return raw data as fallback
            return f"{data.get('date', 'Unknown time')}: {data.get('value', 'No value')} {self.parameters[parameter_choice]['unit']}"
    def run(self):
        """Main application loop."""
        self.console.print("[bold blue]Welcome to Sweden Weather Terminal UI[/bold blue]")
        
        while True:
            # Get parameter choice
            choice = self.display_parameters()
            if choice is None:  # User chose to quit
                break
                
            parameter_id = self.parameters[choice]["id"]  # Get the SMHI parameter ID
            
            # Show loading animation while fetching stations
            with Progress() as progress:
                task = progress.add_task("[cyan]Fetching stations...", total=None)
                stations = self.get_stations(parameter_id)
            
            # Get station choice
            station_id = self.display_stations(stations)
            if station_id is None:  # User chose to go back
                continue
            
            # Get and display weather data
            with Progress() as progress:
                task = progress.add_task("[cyan]Fetching weather data...", total=None)
                weather_data = self.get_latest_weather(parameter_id, station_id)
            
            if weather_data:
                station_name = next(
                    station["name"] 
                    for station in stations 
                    if str(station["key"]) == station_id
                )
                
                self.console.print("\n[bold green]Latest Weather Data[/bold green]")
                self.console.print(f"[yellow]Station:[/yellow] {station_name}")
                self.console.print(
                    f"[yellow]Measurement:[/yellow] {self.format_weather_data(weather_data, choice)}"  # Pass menu choice instead of parameter_id
                )
            else:
                self.console.print("[red]No weather data available for this station.[/red]")
            
            # Ask if user wants to check another location
            if input("\nCheck another location? (y/n): ").lower() != 'y':
                break
        
        self.console.print("[bold blue]Thank you for using Sweden Weather Terminal UI![/bold blue]")

if __name__ == "__main__":
    weather_ui = SwedenWeatherUI()
    weather_ui.run()
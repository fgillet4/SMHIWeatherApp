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
import websockets
import asyncio
from PIL import Image
from io import BytesIO

class SMHIBaseService:
    """Base class for all SMHI services"""
    def __init__(self):
        self.console = Console()
        self.favorites = {}
        self.load_favorites()

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
            self.favorites = {}
        except Exception as e:
            self.console.print(f"[yellow]Could not load favorites: {e}[/yellow]")
            self.favorites = {}

    def fetch_data(self, url: str, is_binary: bool = False) -> Dict:
        """Fetch data from SMHI API."""
        try:
            self.console.print(f"[dim]Fetching URL: {url}[/dim]")
            response = requests.get(url)
            response.raise_for_status()
            if is_binary:
                return response.content
            data = response.json()
            self.console.print("[dim]Data fetched successfully[/dim]")
            return data
        except requests.RequestException as e:
            self.console.print(f"[red]Error fetching data: {e}[/red]")
            raise

class SMHIMultiService:
    """Main class handling multiple SMHI services"""
    def __init__(self):
        self.console = Console()
        self.met_obs = MeteorologicalObservations()
        self.met_forecast = MeteorologicalForecasts()
        self.met_analysis = MeteorologicalAnalysis()
        self.ocean_data = OceanographicData()
        
        self.services = {
            "1": ("Meteorological Observations", self.show_met_observations),
            "2": ("Meteorological Forecasts", self.show_met_forecasts),
            "3": ("Meteorological Analysis (MESAN)", self.show_met_analysis),
            "4": ("Oceanographic Data", self.show_ocean_data),
        }

    def display_main_menu(self) -> Optional[str]:
        """Display main service selection menu"""
        table = Table(title="SMHI Services")
        table.add_column("Option", justify="right", style="cyan")
        table.add_column("Service", style="green")
        
        for key, (service_name, _) in self.services.items():
            table.add_row(key, service_name)
            
        self.console.print(table)
        choice = input("\nSelect a service (1-4) or 'q' to quit: ")
        return None if choice.lower() == 'q' else choice

    def show_met_observations(self):
        """Run the existing meteorological observations interface"""
        self.met_obs.run()

    async def show_met_forecasts(self):
        """Handle meteorological forecast display"""
        lat = float(input("Enter latitude (e.g. 59.3293): "))
        lon = float(input("Enter longitude (e.g. 18.0686): "))
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Fetching forecast...", total=None)
            forecast = await self.met_forecast.get_forecast(lat, lon)
        
        if forecast:
            self.console.print("\n[bold green]Weather Forecast[/bold green]")
            for time_series in forecast['timeSeries'][:24]:  # Next 24 hours
                timestamp = datetime.fromisoformat(time_series['validTime'].replace('Z', '+00:00'))
                temp = next(p['values'][0] for p in time_series['parameters'] if p['name'] == 't')
                self.console.print(f"{timestamp.strftime('%Y-%m-%d %H:%M')}: {temp}°C")

    async def show_met_analysis(self):
        """Handle meteorological analysis display"""
        await self.met_analysis.run_analysis()

    def show_ocean_data(self):
        """Handle oceanographic data display"""
        stations = self.ocean_data.get_stations()
        # Display stations and handle user selection...
        pass

    async def run(self):
        """Main application loop"""
        self.console.print("[bold blue]Welcome to SMHI Multi-Service Terminal UI[/bold blue]")
        
        while True:
            choice = self.display_main_menu()
            if choice is None:
                break
                
            if choice in self.services:
                service_name, handler = self.services[choice]
                self.console.print(f"\n[bold green]Selected Service: {service_name}[/bold green]")
                
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
            else:
                self.console.print("[red]Invalid choice. Please try again.[/red]")
            
            if input("\nReturn to main menu? (y/n): ").lower() != 'y':
                break
        
        self.console.print("[bold blue]Thank you for using SMHI Multi-Service Terminal UI![/bold blue]")

class MeteorologicalObservations(SMHIBaseService):
    """Your existing meteorological observations class"""
    def __init__(self):
        super().__init__()
        self.base_url = "https://opendata-download-metobs.smhi.se/api"
        self.parameters = {
            "1": {"name": "Lufttemperatur momentanvärde, 1 gång/tim", "id": "2", "unit": "°C", "description": "Temperature"},
            "2": {"name": "Lufttryck reducerat havsytans nivå", "id": "9", "unit": "hPa", "description": "Air pressure"},
            "3": {"name": "Relativ Luftfuktighet momentanvärde, 1 gång/tim", "id": "6", "unit": "%", "description": "Relative humidity"},
            "4": {"name": "Nederbördsmängd summa 1 timme, 1 gång/tim", "id": "7", "unit": "mm", "description": "Precipitation amount"},
            "5": {"name": "Vindhastighet medelvärde 10 min, 1 gång/tim", "id": "4", "unit": "m/s", "description": "Wind speed"}
        }
        self.period_types = ["latest-hour", "latest-day", "latest-months"]
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
class MeteorologicalForecasts(SMHIBaseService):
    """Handle meteorological forecasts"""
    def __init__(self):
        super().__init__()
        self.base_url = "https://opendata-download-metfcst.smhi.se/api"

    async def get_forecast(self, lat: float, lon: float) -> Dict:
        url = f"{self.base_url}/category/pmp3g/version/2/geotype/point/lon/{lon}/lat/{lat}/data.json"
        return self.fetch_data(url)

class OceanographicData(SMHIBaseService):
    """Handle oceanographic observations"""
    def __init__(self):
        super().__init__()
        self.base_url = "https://opendata-download-ocobs.smhi.se/api"

    def get_stations(self) -> List[Dict]:
        url = f"{self.base_url}/version/latest/parameter/1.json"
        data = self.fetch_data(url)
        return data.get("station", [])
class MeteorologicalAnalysis(SMHIBaseService):
    """Handle MESAN meteorological analysis data"""
    def __init__(self):
        super().__init__()
        self.base_url = "https://opendata-download-metanalys.smhi.se/api"
        self.parameters = {
            "1": {"name": "t", "description": "Temperature", "unit": "°C", "level_type": "hl", "level": 2},
            "2": {"name": "gust", "description": "Wind gust", "unit": "m/s", "level_type": "hl", "level": 10},
            "3": {"name": "r", "description": "Relative humidity", "unit": "%", "level_type": "hl", "level": 2},
            "4": {"name": "msl", "description": "Air pressure", "unit": "hPa", "level_type": "hmsl", "level": 0},
            "5": {"name": "vis", "description": "Visibility", "unit": "km", "level_type": "hl", "level": 2},
            "6": {"name": "ws", "description": "Wind speed", "unit": "m/s", "level_type": "hl", "level": 10},
            "7": {"name": "wd", "description": "Wind direction", "unit": "degree", "level_type": "hl", "level": 10}
        }

    async def get_analysis(self, lat: float, lon: float) -> Dict:
        """Get meteorological analysis for specific coordinates"""
        url = f"{self.base_url}/category/mesan2g/version/1/geotype/point/lon/{lon}/lat/{lat}/data.json"
        return self.fetch_data(url)

    def format_analysis_data(self, data: Dict, parameter: str) -> List[Dict]:
        """Format analysis data for display"""
        formatted_data = []
        param_info = self.parameters[parameter]
        param_name = param_info["name"]
        
        for time_series in data.get("timeSeries", []):
            timestamp = datetime.fromisoformat(time_series["validTime"].replace('Z', '+00:00'))
            
            # Find the parameter in the time series
            param_data = next(
                (p for p in time_series["parameters"] if p["name"] == param_name),
                None
            )
            
            if param_data:
                value = param_data["values"][0]
                formatted_data.append({
                    "timestamp": timestamp,
                    "value": value,
                    "unit": param_info["unit"]
                })
                
        return formatted_data

    def display_parameters(self) -> Optional[str]:
        """Display available parameters and get user selection"""
        table = Table(title="Available Analysis Parameters")
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
        
        choice = input("\nSelect a parameter (1-7) or 'q' to quit: ")
        return None if choice.lower() == 'q' else choice

    async def run_analysis(self):
            """Main analysis interface"""
            self.console.print("[bold blue]SMHI Meteorological Analysis (MESAN)[/bold blue]")
            
            # Get location
            location_util = LocationUtil()
            try:
                lat, lon = await location_util.get_location()
            except Exception as e:
                self.console.print(f"[red]Error getting location: {str(e)}[/red]")
                return

            # Get parameter choice
            choice = self.display_parameters()
            if choice is None:
                return

            if choice not in self.parameters:
                self.console.print("[red]Invalid parameter choice.[/red]")
                return

            # Fetch and display data
            try:
                with Progress() as progress:
                    task = progress.add_task("[cyan]Fetching analysis data...", total=None)
                    data = await self.get_analysis(lat, lon)

                if data:
                    formatted_data = self.format_analysis_data(data, choice)
                    
                    if formatted_data:
                        self.console.print(f"\n[bold green]Analysis Results for {self.parameters[choice]['description']}[/bold green]")
                        self.console.print(f"[yellow]Location:[/yellow] {lat}°N, {lon}°E")
                        self.console.print(f"[yellow]Reference Time:[/yellow] {data['referenceTime']}")
                        self.console.print(f"[yellow]Approved Time:[/yellow] {data['approvedTime']}")
                        
                        # Create table for results
                        results_table = Table(title="Analysis Results")
                        results_table.add_column("Time", style="cyan")
                        results_table.add_column("Value", style="green")
                        results_table.add_column("Unit", style="blue")
                        
                        for item in formatted_data:
                            results_table.add_row(
                                item["timestamp"].strftime("%Y-%m-%d %H:%M"),
                                f"{item['value']:.1f}",
                                item["unit"]
                            )
                        
                        self.console.print(results_table)
                    else:
                        self.console.print("[yellow]No data available for the selected parameter.[/yellow]")
                else:
                    self.console.print("[red]No analysis data available for this location.[/red]")
                    
            except Exception as e:
                self.console.print(f"[red]Error getting analysis data: {str(e)}[/red]")
class LocationUtil:
    """Utility class for handling location data"""
    def __init__(self):
        self.console = Console()

    async def get_location(self) -> tuple[float, float]:
        """Get location either automatically or manually"""
        self.console.print("\n[bold]Location Input[/bold]")
        choice = input("Would you like to: \n1. Get location automatically\n2. Enter location manually\nChoice (1/2): ")

        if choice == "1":
            try:
                lat, lon = await self.get_automatic_location()
                self.console.print(f"[green]Located at: {lat}°N, {lon}°E[/green]")
                if input("Use this location? (y/n): ").lower() != 'y':
                    return await self.get_manual_location()
                return lat, lon
            except Exception as e:
                self.console.print(f"[yellow]Could not get automatic location: {str(e)}[/yellow]")
                self.console.print("[yellow]Falling back to manual input...[/yellow]")
                return await self.get_manual_location()
        else:
            return await self.get_manual_location()

    async def get_automatic_location(self) -> tuple[float, float]:
        """Get location automatically using IP-based geolocation"""
        try:
            with Progress() as progress:
                task = progress.add_task("[cyan]Getting location...", total=None)
                response = requests.get('https://ipapi.co/json/')
                response.raise_for_status()
                data = response.json()
                
                # Extract coordinates
                lat = float(data.get('latitude', 0))
                lon = float(data.get('longitude', 0))
                
                if lat == 0 and lon == 0:
                    raise ValueError("Could not determine location")
                    
                return lat, lon
        except Exception as e:
            raise Exception(f"Error getting automatic location: {str(e)}")

    async def get_manual_location(self) -> tuple[float, float]:
        """Get location through manual input"""
        while True:
            try:
                lat = float(input("Enter latitude (-90 to 90, e.g. 57.694660): "))
                if not -90 <= lat <= 90:
                    raise ValueError("Latitude must be between -90 and 90")
                
                lon = float(input("Enter longitude (-180 to 180, e.g. 11.979730): "))
                if not -180 <= lon <= 180:
                    raise ValueError("Longitude must be between -180 and 180")
                
                return lat, lon
            except ValueError as e:
                self.console.print(f"[red]Invalid input: {str(e)}[/red]")
                continue

if __name__ == "__main__":
    service = SMHIMultiService()
    asyncio.run(service.run())
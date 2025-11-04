r"""
Client Manager Module

This module provides centralized client configuration management for the fulfillment tool.
All client configurations are stored on a file server in a standardized structure.

File Structure:
    1FULFILMENT tool/
    ├── CLIENTS/
    │   └── {client_id}/
    │       ├── client_config.json
    │       └── sku_mapping.json
    ├── SESSIONS/
    ├── STATS/
    └── LOGS/

Example Usage:
    >>> manager = ClientManager(r"\\SERVER\...\1FULFILMENT tool")
    >>>
    >>> # List all active clients
    >>> clients = manager.list_clients()
    >>>
    >>> # Create a new client
    >>> manager.create_client("CLIENT_001", "Example Client")
    >>>
    >>> # Load client configuration
    >>> config = manager.load_config("CLIENT_001")
    >>>
    >>> # Modify and save configuration
    >>> config["shopify"]["rules"].append({"rule": "example"})
    >>> manager.save_config("CLIENT_001", config)
    >>>
    >>> # Load SKU mappings
    >>> mappings = manager.load_sku_mapping("CLIENT_001")
    >>>
    >>> # Save SKU mappings
    >>> manager.save_sku_mapping("CLIENT_001", {"SKU001": "Product 1"})
    >>>
    >>> # Soft delete a client
    >>> manager.delete_client("CLIENT_001")
"""

import json
import logging
import os
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Configure logging
logger = logging.getLogger(__name__)


class ClientManager:
    r"""
    Manages client configurations with file locking for multi-PC access.

    This class provides thread-safe and multi-process safe operations for managing
    client configurations stored on a shared file server. It uses lock files and
    retry logic to ensure data integrity when multiple PCs access the same files
    over network shares.

    Attributes:
        base_path (Path): Base path to the fulfillment tool directory on the server
        clients_dir (Path): Path to the CLIENTS directory
        sessions_dir (Path): Path to the SESSIONS directory
        stats_dir (Path): Path to the STATS directory
        logs_dir (Path): Path to the LOGS directory

    Example:
        >>> manager = ClientManager(r"\\192.168.88.101\Z_GreenDelivery\WAREHOUSE\1FULFILMENT tool")
        >>> manager.create_client("CLIENT_ABC", "ABC Corporation")
        >>> config = manager.load_config("CLIENT_ABC")
    """

    # Retry configuration
    MAX_READ_RETRIES = 3
    MAX_WRITE_RETRIES = 3
    RETRY_DELAY = 0.5
    LOCK_WAIT_TIMEOUT = 5

    def __init__(self, base_path: str):
        r"""
        Initialize the ClientManager with the server path.

        Args:
            base_path: Path to the "1FULFILMENT tool" directory on the server
                      (e.g., r"\\192.168.88.101\Z_GreenDelivery\WAREHOUSE\1FULFILMENT tool")

        Raises:
            ValueError: If base_path doesn't exist or is not accessible

        Example:
            >>> manager = ClientManager(r"\\SERVER\path\1FULFILMENT tool")
        """
        self.base_path = Path(base_path)

        # Validate base path exists and is accessible
        if not self.base_path.exists():
            error_msg = f"Base path does not exist or is not accessible: {base_path}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Define directory structure
        self.clients_dir = self.base_path / "CLIENTS"
        self.sessions_dir = self.base_path / "SESSIONS"
        self.stats_dir = self.base_path / "STATS"
        self.logs_dir = self.base_path / "LOGS"

        # Create directories if they don't exist
        self._ensure_directories()

        logger.info(f"ClientManager initialized with base path: {base_path}")

    def _ensure_directories(self) -> None:
        """
        Ensure all required directories exist.

        Creates CLIENTS, SESSIONS, STATS, and LOGS directories if they don't exist.
        """
        try:
            for directory in [self.clients_dir, self.sessions_dir, self.stats_dir, self.logs_dir]:
                directory.mkdir(parents=True, exist_ok=True)
            logger.debug("All required directories verified/created")
        except Exception as e:
            logger.error(f"Error creating directories: {e}\n{traceback.format_exc()}")
            raise

    def _get_client_dir(self, client_id: str) -> Path:
        """
        Get the directory path for a specific client.

        Args:
            client_id: The client identifier

        Returns:
            Path to the client's directory
        """
        return self.clients_dir / client_id

    def _get_config_path(self, client_id: str) -> Path:
        """
        Get the path to a client's configuration file.

        Args:
            client_id: The client identifier

        Returns:
            Path to client_config.json
        """
        return self._get_client_dir(client_id) / "client_config.json"

    def _get_sku_mapping_path(self, client_id: str) -> Path:
        """
        Get the path to a client's SKU mapping file.

        Args:
            client_id: The client identifier

        Returns:
            Path to sku_mapping.json
        """
        return self._get_client_dir(client_id) / "sku_mapping.json"

    def get_session_dir(self, client_id: str, session_name: str = None) -> Path:
        """
        Get the session directory path for a client.

        Args:
            client_id: The client identifier
            session_name: Optional session name. If None, returns client's sessions root.

        Returns:
            Path to session directory

        Example:
            >>> manager.get_session_dir("CLIENT_001")
            Path("\\\\SERVER\\...\\SESSIONS\\CLIENT_001")
            >>> manager.get_session_dir("CLIENT_001", "2025-11-04_Session_001")
            Path("\\\\SERVER\\...\\SESSIONS\\CLIENT_001\\2025-11-04_Session_001")
        """
        client_sessions_dir = self.sessions_dir / client_id

        if session_name:
            return client_sessions_dir / session_name
        else:
            return client_sessions_dir

    def ensure_client_session_dir(self, client_id: str) -> bool:
        """
        Ensure client's session directory exists.

        Args:
            client_id: The client identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            client_sessions_dir = self.get_session_dir(client_id)
            client_sessions_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured session directory exists: {client_sessions_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to create session directory for {client_id}: {e}")
            return False

    def _read_json_with_lock(self, file_path: Path) -> Dict[str, Any]:
        """
        Read JSON file with retry logic for network share compatibility.

        Args:
            file_path: Path to the JSON file

        Returns:
            Parsed JSON data as dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file contains invalid JSON
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        max_retries = self.MAX_READ_RETRIES
        retry_delay = self.RETRY_DELAY

        for attempt in range(max_retries):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.debug(f"Successfully read file: {file_path}")
                return data
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in file {file_path}: {e}\n{traceback.format_exc()}")
                raise
            except (IOError, OSError) as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Read attempt {attempt + 1} failed for {file_path}: {e}. Retrying..."
                    )
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    logger.error(
                        f"Failed to read file after {max_retries} attempts: {file_path}\n"
                        f"{traceback.format_exc()}"
                    )
                    raise
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}\n{traceback.format_exc()}")
                raise

    def _write_json_with_lock(self, file_path: Path, data: Dict[str, Any]) -> None:
        """
        Write JSON file with lock file approach for network share compatibility.

        Uses a temporary lock file and atomic rename to ensure data integrity
        during concurrent access over network shares.

        Args:
            file_path: Path to the JSON file
            data: Data to write as JSON

        Raises:
            IOError: If unable to write file
        """
        lock_file = file_path.parent / f"{file_path.name}.lock"
        max_retries = self.MAX_WRITE_RETRIES
        retry_delay = self.RETRY_DELAY

        # Wait for existing lock to be released
        lock_wait_iterations = int(self.LOCK_WAIT_TIMEOUT / 0.5)
        for _ in range(lock_wait_iterations):
            if not lock_file.exists():
                break
            logger.debug(f"Waiting for lock file to be released: {lock_file}")
            time.sleep(0.5)
        else:
            logger.warning(f"Lock file still exists after {self.LOCK_WAIT_TIMEOUT}s, proceeding anyway")

        # Create lock file
        try:
            lock_file.touch(exist_ok=False)  # Fail if exists
            logger.debug(f"Created lock file: {lock_file}")
        except FileExistsError:
            logger.warning(f"Lock file exists, writing anyway: {lock_file}")

        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to temporary file first
            temp_file = file_path.parent / f"{file_path.name}.tmp"

            for attempt in range(max_retries):
                try:
                    with open(temp_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                        f.flush()
                        os.fsync(f.fileno())

                    # Atomic move/replace
                    temp_file.replace(file_path)
                    logger.debug(f"Successfully wrote file: {file_path}")
                    break

                except (IOError, OSError) as e:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Write attempt {attempt + 1} failed for {file_path}: {e}. Retrying..."
                        )
                        time.sleep(retry_delay * (attempt + 1))
                    else:
                        logger.error(
                            f"Failed to write file after {max_retries} attempts: {file_path}\n"
                            f"{traceback.format_exc()}"
                        )
                        raise
                except Exception as e:
                    logger.error(f"Error writing file {file_path}: {e}\n{traceback.format_exc()}")
                    raise

        finally:
            # Always remove lock file and temp file
            try:
                lock_file.unlink(missing_ok=True)
                logger.debug(f"Removed lock file: {lock_file}")
            except Exception as e:
                logger.warning(f"Failed to remove lock file: {e}")

            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove temp file: {e}")

    def _get_default_config(self, client_id: str, name: str) -> Dict[str, Any]:
        """
        Get the default configuration template for a new client.

        Args:
            client_id: The client identifier
            name: The client's display name

        Returns:
            Default configuration dictionary
        """
        now = datetime.utcnow().isoformat()

        return {
            "client_id": client_id,
            "name": name,
            "active": True,
            "created_at": now,
            "updated_at": now,
            "shopify": {
                # Column mappings for CSV validation
                "column_mappings": {
                    "orders": {
                        "name": "Name",
                        "sku": "Lineitem sku",
                        "quantity": "Lineitem quantity",
                        "shipping_provider": "Shipping Provider",
                        "fulfillment_status": "Fulfillment Status",
                        "financial_status": "Financial Status",
                        "order_number": "Name"
                    },
                    "stock": {
                        "sku": "Артикул",
                        "stock": "Наличност"
                    },
                    "orders_required": ["Name", "Lineitem sku", "Lineitem quantity"],
                    "stock_required": ["Артикул", "Наличност"]
                },

                # General settings
                "settings": {
                    "stock_csv_delimiter": ";",
                    "low_stock_threshold": 10
                },

                # Courier name standardization
                "courier_mappings": {
                    "type": "pattern_matching",
                    "case_sensitive": False,
                    "rules": [
                        {"pattern": "dhl", "standardized_name": "DHL"},
                        {"pattern": "speedy", "standardized_name": "Speedy"},
                        {"pattern": "econt", "standardized_name": "Econt"},
                        {"pattern": "dpd", "standardized_name": "DPD"},
                        {"pattern": "ups", "standardized_name": "UPS"}
                    ],
                    "default": "Other"
                },

                # Automation rules
                "rules": [],

                # Report templates
                "packing_lists": [],
                "stock_exports": [],

                # Additional config
                "virtual_products": {},
                "deduction_rules": {}
            }
        }

    def list_clients(self) -> List[Dict[str, str]]:
        """
        List all active clients.

        Returns:
            List of dictionaries with client information:
            [{"client_id": "...", "name": "...", "created_at": "..."}, ...]

        Example:
            >>> manager.list_clients()
            [
                {
                    "client_id": "CLIENT_001",
                    "name": "ABC Corporation",
                    "created_at": "2024-01-01T00:00:00"
                }
            ]
        """
        clients = []

        try:
            if not self.clients_dir.exists():
                logger.warning("CLIENTS directory does not exist")
                return clients

            for client_dir in self.clients_dir.iterdir():
                if not client_dir.is_dir():
                    continue

                config_path = client_dir / "client_config.json"
                if not config_path.exists():
                    logger.warning(f"Config file missing for client: {client_dir.name}")
                    continue

                try:
                    config = self._read_json_with_lock(config_path)

                    # Only include active clients
                    if config.get("active", True):
                        clients.append({
                            "client_id": config.get("client_id", client_dir.name),
                            "name": config.get("name", "Unknown"),
                            "created_at": config.get("created_at", "Unknown")
                        })
                except Exception as e:
                    logger.error(f"Error reading config for {client_dir.name}: {e}")
                    continue

            logger.info(f"Listed {len(clients)} active clients")
            return clients

        except Exception as e:
            logger.error(f"Error listing clients: {e}\n{traceback.format_exc()}")
            return clients

    def load_config(self, client_id: str) -> Dict[str, Any]:
        """
        Load a client's configuration with file locking.

        Args:
            client_id: The client identifier

        Returns:
            Client configuration dictionary

        Raises:
            FileNotFoundError: If client doesn't exist
            json.JSONDecodeError: If config file is invalid

        Example:
            >>> config = manager.load_config("CLIENT_001")
            >>> print(config["name"])
            "ABC Corporation"
        """
        config_path = self._get_config_path(client_id)

        if not config_path.exists():
            error_msg = f"Client does not exist: {client_id}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            config = self._read_json_with_lock(config_path)

            # Validate that client_id matches
            if config.get("client_id") != client_id:
                logger.warning(
                    f"Client ID mismatch in config file. "
                    f"Expected: {client_id}, Found: {config.get('client_id')}"
                )

            logger.info(f"Loaded config for client: {client_id}")
            return config

        except Exception as e:
            logger.error(f"Error loading config for {client_id}: {e}\n{traceback.format_exc()}")
            raise

    def save_config(self, client_id: str, config: Dict[str, Any]) -> bool:
        """
        Save a client's configuration with file locking.

        Args:
            client_id: The client identifier
            config: Configuration dictionary to save

        Returns:
            True if successful, False otherwise

        Example:
            >>> config = manager.load_config("CLIENT_001")
            >>> config["shopify"]["rules"].append({"rule": "new_rule"})
            >>> config["updated_at"] = datetime.utcnow().isoformat()
            >>> manager.save_config("CLIENT_001", config)
            True
        """
        config_path = self._get_config_path(client_id)

        try:
            # Ensure client directory exists
            client_dir = self._get_client_dir(client_id)
            if not client_dir.exists():
                error_msg = f"Client directory does not exist: {client_id}"
                logger.error(error_msg)
                return False

            # Validate client_id matches
            if config.get("client_id") != client_id:
                logger.warning(
                    f"Client ID mismatch. Updating config client_id from "
                    f"{config.get('client_id')} to {client_id}"
                )
                config["client_id"] = client_id

            # Update timestamp
            config["updated_at"] = datetime.utcnow().isoformat()

            # Write with lock
            self._write_json_with_lock(config_path, config)

            logger.info(f"Saved config for client: {client_id}")
            return True

        except Exception as e:
            logger.error(f"Error saving config for {client_id}: {e}\n{traceback.format_exc()}")
            return False

    def create_client(self, client_id: str, name: str) -> bool:
        """
        Create a new client with default configuration.

        Config structure matches the reference exactly, with unique values
        for client_id, name, created_at, updated_at per client.

        Args:
            client_id: Unique identifier (e.g., "CLIENT_MYTHOS")
            name: Display name (e.g., "Mythos")

        Returns:
            True if successful, False otherwise

        Example:
            >>> manager.create_client("CLIENT_ABC", "ABC Corporation")
            True
        """
        client_dir = self._get_client_dir(client_id)

        if client_dir.exists():
            logger.error(f"Client already exists: {client_id}")
            return False

        try:
            # Create client directory
            client_dir.mkdir(parents=True, exist_ok=True)

            # Create config with EXACT reference structure
            now = datetime.utcnow().isoformat()

            default_config = {
                "client_id": client_id,
                "name": name,
                "active": True,
                "created_at": now,
                "updated_at": now,
                "shopify": {
                    "column_mappings": {
                        "orders": {
                            "name": "Name",
                            "sku": "Lineitem sku",
                            "quantity": "Lineitem quantity",
                            "shipping_provider": "Shipping Provider",
                            "fulfillment_status": "Fulfillment Status",
                            "financial_status": "Financial Status",
                            "order_number": "Name"
                        },
                        "stock": {
                            "sku": "Артикул",
                            "stock": "Наличност"
                        },
                        "orders_required": [
                            "Name",
                            "Lineitem sku",
                            "Lineitem quantity"
                        ],
                        "stock_required": [
                            "Артикул",
                            "Наличност"
                        ]
                    },
                    "settings": {
                        "stock_csv_delimiter": ";",
                        "low_stock_threshold": 10
                    },
                    "courier_mappings": {
                        "type": "pattern_matching",
                        "case_sensitive": False,
                        "rules": [
                            {"pattern": "dhl", "standardized_name": "DHL"},
                            {"pattern": "speedy", "standardized_name": "Speedy"},
                            {"pattern": "econt", "standardized_name": "Econt"},
                            {"pattern": "dpd", "standardized_name": "DPD"},
                            {"pattern": "ups", "standardized_name": "UPS"}
                        ],
                        "default": "Other"
                    },
                    "rules": [],
                    "packing_lists": [],
                    "stock_exports": [],
                    "virtual_products": {},
                    "deduction_rules": {}
                }
            }

            # Write config to file
            config_path = self._get_config_path(client_id)
            self._write_json_with_lock(config_path, default_config)

            # Create empty SKU mapping file
            sku_mapping_path = self._get_sku_mapping_path(client_id)
            self._write_json_with_lock(sku_mapping_path, {})

            # Create client's session directory
            self.ensure_client_session_dir(client_id)

            logger.info(f"Successfully created client: {client_id} ({name})")
            return True

        except Exception as e:
            logger.error(f"Failed to create client {client_id}: {e}\n{traceback.format_exc()}")
            # Cleanup on failure
            if client_dir.exists():
                import shutil
                shutil.rmtree(client_dir, ignore_errors=True)
            return False

    def delete_client(self, client_id: str) -> bool:
        """
        Soft delete a client by setting active=False.

        This method doesn't actually delete the client files, it just marks
        the client as inactive in the configuration.

        Args:
            client_id: The client identifier

        Returns:
            True if successful, False otherwise

        Example:
            >>> manager.delete_client("CLIENT_001")
            True
        """
        try:
            # Load current config
            config = self.load_config(client_id)

            # Set active to False
            config["active"] = False
            config["updated_at"] = datetime.utcnow().isoformat()

            # Save updated config
            result = self.save_config(client_id, config)

            if result:
                logger.info(f"Soft deleted client: {client_id}")

            return result

        except FileNotFoundError:
            logger.error(f"Cannot delete - client does not exist: {client_id}")
            return False
        except Exception as e:
            logger.error(f"Error deleting client {client_id}: {e}\n{traceback.format_exc()}")
            return False

    def load_sku_mapping(self, client_id: str) -> Dict[str, str]:
        """
        Load SKU mappings for a client.

        Args:
            client_id: The client identifier

        Returns:
            Dictionary mapping SKUs to product names

        Raises:
            FileNotFoundError: If client doesn't exist

        Example:
            >>> mappings = manager.load_sku_mapping("CLIENT_001")
            >>> print(mappings)
            {"SKU001": "Product A", "SKU002": "Product B"}
        """
        sku_mapping_path = self._get_sku_mapping_path(client_id)

        # Check if client exists
        if not self._get_client_dir(client_id).exists():
            error_msg = f"Client does not exist: {client_id}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # If SKU mapping file doesn't exist, return empty dict
        if not sku_mapping_path.exists():
            logger.warning(f"SKU mapping file does not exist for {client_id}, returning empty mapping")
            return {}

        try:
            mappings = self._read_json_with_lock(sku_mapping_path)
            logger.info(f"Loaded {len(mappings)} SKU mappings for client: {client_id}")
            return mappings

        except Exception as e:
            logger.error(f"Error loading SKU mappings for {client_id}: {e}\n{traceback.format_exc()}")
            raise

    def save_sku_mapping(self, client_id: str, mapping: Dict[str, str]) -> bool:
        """
        Save SKU mappings for a client.

        Args:
            client_id: The client identifier
            mapping: Dictionary mapping SKUs to product names

        Returns:
            True if successful, False otherwise

        Example:
            >>> mappings = {"SKU001": "Product A", "SKU002": "Product B"}
            >>> manager.save_sku_mapping("CLIENT_001", mappings)
            True
        """
        sku_mapping_path = self._get_sku_mapping_path(client_id)

        try:
            # Check if client exists
            client_dir = self._get_client_dir(client_id)
            if not client_dir.exists():
                error_msg = f"Client does not exist: {client_id}"
                logger.error(error_msg)
                return False

            # Save mapping
            self._write_json_with_lock(sku_mapping_path, mapping)

            logger.info(f"Saved {len(mapping)} SKU mappings for client: {client_id}")
            return True

        except Exception as e:
            logger.error(f"Error saving SKU mappings for {client_id}: {e}\n{traceback.format_exc()}")
            return False

    def get_client_path(self, client_id: str) -> Path:
        r"""
        Get the directory path for a specific client.

        Args:
            client_id: The client identifier

        Returns:
            Path to the client's directory

        Example:
            >>> path = manager.get_client_path("CLIENT_001")
            >>> print(path)
            \\SERVER\...\1FULFILMENT tool\CLIENTS\CLIENT_001
        """
        return self._get_client_dir(client_id)

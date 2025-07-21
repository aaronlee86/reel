import os
from typing import Optional, List, Union

class FileResolver:
    @staticmethod
    def resolve_file_path(
        filename: str, 
        project_name: str, 
        search_paths: Optional[List[str]] = None,
        file_types: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Resolve file path with flexible search strategy
        
        Args:
            filename (str): Name of the file to find
            project_name (str): Current project name
            search_paths (Optional[List[str]]): Custom search paths (optional)
            file_types (Optional[List[str]]): Allowed file extensions (optional)
        
        Returns:
            Optional[str]: Resolved absolute file path or None if not found
        """
        # Default search paths if not provided
        if search_paths is None:
            search_paths = [
                os.path.join('workspace', project_name),  # First priority: project workspace
                os.path.join('assets', 'img'),            # Second priority: assets/img
                os.path.join('assets', 'video'),          # Third priority: assets/video
                os.path.join('assets', 'audio'),          # Fourth priority: assets/audio
                os.path.curdir                            # Last resort: current directory
            ]
        
        # Validate filename
        if not filename or not isinstance(filename, str):
            return None
        
        # If absolute path is provided and exists, return it
        if os.path.isabs(filename) and os.path.exists(filename):
            return filename
        
        # Search through specified paths
        for search_path in search_paths:
            # Construct full path
            full_path = os.path.join(search_path, filename)
            
            # Check if file exists
            if os.path.exists(full_path):
                # If file types are specified, check extension
                if file_types:
                    _, ext = os.path.splitext(full_path)
                    if ext.lstrip('.') in file_types:
                        return full_path
                else:
                    return full_path
        
        # File not found
        return None

    @staticmethod
    def list_files(
        project_name: str, 
        search_paths: Optional[List[str]] = None,
        file_types: Optional[List[str]] = None
    ) -> List[str]:
        """
        List files in specified paths
        
        Args:
            project_name (str): Current project name
            search_paths (Optional[List[str]]): Custom search paths
            file_types (Optional[List[str]]): Filter by file extensions
        
        Returns:
            List[str]: List of found files
        """
        # Default search paths if not provided
        if search_paths is None:
            search_paths = [
                os.path.join('workspace', project_name),
                os.path.join('assets', 'img'),
                os.path.join('assets', 'video'),
                os.path.join('assets', 'audio')
            ]
        
        found_files = []
        
        for search_path in search_paths:
            # Ensure path exists
            if not os.path.exists(search_path) or not os.path.isdir(search_path):
                continue
            
            # List files in directory
            for filename in os.listdir(search_path):
                full_path = os.path.join(search_path, filename)
                
                # Skip directories
                if os.path.isdir(full_path):
                    continue
                
                # Check file type if specified
                if file_types:
                    _, ext = os.path.splitext(filename)
                    if ext.lstrip('.') not in file_types:
                        continue
                
                found_files.append(full_path)
        
        return found_files

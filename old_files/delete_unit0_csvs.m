function delete_unit0_csvs(folders)
%DELETE_UNIT0_CSVS Delete all *_unit_0.csv files in given folders.
%  delete_unit0_csvs(folders) accepts a string/char array or cell array of
%  folder paths. If folders is omitted, the function prompts to select
%  folders (Cancel to finish).
%
%  Example:
%    delete_unit0_csvs(folders)   % pass the same folders used by your main script
%    delete_unit0_csvs()          % interactive selection

if nargin < 1 || isempty(folders)
    folders = string.empty;
    while true
        dlg = uigetdir(pwd, 'Select a folder to delete *_unit_0.csv (Cancel to finish)');
        if dlg == 0
            break;
        end
        folders(end+1) = string(dlg); %#ok<SAGROW>
    end
    if isempty(folders)
        fprintf('No folders selected. Nothing to delete.\n');
        return;
    end
end

% Normalize to string array
if iscell(folders)
    folders = string(folders);
else
    folders = string(folders);
end

deletedAny = false;
for i = 1:numel(folders)
    folderPath = folders(i);
    if ~isfolder(folderPath)
        fprintf('Skipping non-existent folder: %s\n', folderPath);
        continue;
    end
    pattern = fullfile(folderPath, '*_unit_0.csv');
    files = dir(pattern);
    if isempty(files)
        fprintf('No *_unit_0.csv files in %s\n', folderPath);
        continue;
    end
    for k = 1:numel(files)
        fname = fullfile(folderPath, files(k).name);
        try
            delete(fname);
            fprintf('Deleted: %s\n', fname);
            deletedAny = true;
        catch ME
            warning('Could not delete %s: %s', fname, ME.message);
        end
    end
end

if ~deletedAny
    fprintf('No files deleted.\n');
end
end

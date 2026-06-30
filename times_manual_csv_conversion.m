% 1. Define the explicit list of folders you want to process
folders = {
   '/Users/aatmi/Aatmi CML work/Clip Capstone alignments/566TMexp7presleep';
   '/Users/aatmi/Aatmi CML work/Clip Capstone alignments/567TMexp8presleep';
   '/Users/aatmi/Aatmi CML work/Clip Capstone alignments/568TMexp5presleep';
   '/Users/aatmi/Aatmi CML work/Clip Capstone alignments/570TMexp4presleep';
   '/Users/aatmi/Aatmi CML work/Clip Capstone alignments/572TMexp9presleepviewing';
   '/Users/aatmi/Aatmi CML work/Clip Capstone alignments/573TMexp7presleepviewing';
   '/Users/aatmi/Aatmi CML work/Clip Capstone alignments/574TMexp10viewing';
   '/Users/aatmi/Aatmi CML work/Clip Capstone alignments/576TMexp14Viewing';
   '/Users/aatmi/Aatmi CML work/Clip Capstone alignments/577TMexp4viewing';
   '/Users/aatmi/Aatmi CML work/Clip Capstone alignments/579TMexp6viewing';
   '/Users/aatmi/Aatmi CML work/Clip Capstone alignments/582TMexp8viewing';
   '/Users/aatmi/Aatmi CML work/Clip Capstone alignments/1717TMexp50viewing';
   '/Users/aatmi/Aatmi CML work/Clip Capstone alignments/1728TMexp45movie24'
};
% 2. Loop through each folder in your specific list
for f = 1:length(folders)
   folderPath = folders{f};
  
   % Check to make sure the folder actually exists before trying to read it
   if isfolder(folderPath)
       fprintf('Processing folder: %s\n', folderPath);
      
       % Get a list of all .mat files that start with "times_manual" in this folder
       matFiles = dir(fullfile(folderPath, 'times_manual*.mat'));
      
       % Loop through each .mat file
       for k = 1:length(matFiles)
           % Load the .mat file
           matFileName = fullfile(folderPath, matFiles(k).name);
           file = load(matFileName);
          
           % Extract the base name of the file (without extension)
           [~, baseName, ~] = fileparts(matFiles(k).name);
           name = baseName;
          
           % Safety check: Ensure 'cluster_class' actually exists in the file to prevent crashes
           if isfield(file, 'cluster_class')
               cluster = file.cluster_class(:, 1:2);
              
               % Get unique units
               units = unique(cluster(:,1));
              
               % Loop through each unit
               for i = 1:length(units)
                   unit = units(i);
                  
                   % Extract data for the current unit
                   table = cluster(cluster(:,1) == unit, :);
                  
                   % Generate the output filename
                   filename = sprintf('%s_unit_%d.csv', fullfile(folderPath, name), unit);
                  
                   % Write data to the CSV file with headers
                   header = ["units", "s"];
                   data_with_header = [header; num2cell(table)];
                   writematrix(data_with_header, filename);
               end
           else
               fprintf('  -> Warning: cluster_class not found in %s. Skipping.\n', matFiles(k).name);
           end
       end
   else
       fprintf('Warning: Folder does not exist, skipping: %s\n', folderPath);
   end
end
fprintf('All listed folders processed successfully!\n');

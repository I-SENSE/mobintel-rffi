function split_signal_fun(fldr_name)
    fileList = dir(['/Users/stepanmazokha/Desktop/wisig_raw_rffi_dataset/' fldr_name,'/*.dat']);

    %flip(fileList);
%     fig=figure(11);
    for fi=1:length(fileList)
        tic;
    
        transmitter=regexp(fileList(fi).name, ['\d+-\d+(?=:*}_rx{node:' , fldr_name,...
            '-rxFreq:2462e6-rxGain:0\.5-capLen:0\.512-rxSampRate:25e6}\.dat)'], 'match');
    
        transmitter=transmitter{1};
    
        fprintf('%d of %d %s:',fi,length(fileList),transmitter);
    
        packet_log = {};
        packet_log_filename = strcat('packets_', transmitter, '.mat');
    
        X = read_complex_binary(['/Users/stepanmazokha/Desktop/wisig_raw_rffi_dataset/',fldr_name,'/',fileList(fi).name]);

        X = X(1:800000);

        % Create a configuration object for an 802.11n packet
        cfgHT = wlanNonHTConfig;
        
        % Generate the reference LTF sequence
        % The function wlanLLTF generates the L-LTF time domain signal for 802.11n
        ltfSequence = wlanLLTF(cfgHT);
        stfSequence = wlanLSTF(cfgHT);
        
        % Perform correlation
        [correlationLTF, lagLTF] = xcorr(X, ltfSequence);
        [correlationSTF, lagSTF] = xcorr(X, stfSequence);

        correlationLTF = abs(correlationLTF);
        correlationSTF = abs(correlationSTF);
        
        % Find peaks in the correlation
        [~, locsLTF] = findpeaks(correlationLTF, 'MinPeakHeight', max(correlationLTF) * 0.8, 'MinPeakDistance', length(ltfSequence));
        [~, locsSTF] = findpeaks(correlationSTF, 'MinPeakHeight', max(correlationSTF) * 0.8, 'MinPeakDistance', length(stfSequence));

        startIndicesLTF = lagLTF(locsLTF);
        startIndicesSTF = lagSTF(locsSTF);
        
        % Optional: Plot the IQ samples and mark the LTF start points
        figure;
        plot(1:length(X), real(X));
        hold on;
        plot(startIndicesLTF, zeros(size(startIndicesLTF, 1)), 'r.');
        plot(startIndicesSTF, zeros(size(startIndicesSTF, 1)), 'g.');
        title('IQ Samples with LTF Start Points');
        xlabel('Sample Index');
        ylabel('Amplitude');
        grid on;
        hold off;
        disp('');




















































    
        en=find_beg(x,1);
    
        final = length(x)-find_beg(flip(x),1);
    
    
        x_r = real(x);  
        xx=x_r;
    
        energies=[];
        maxs=[];
        endpoints=[];
        lengths=[];
    
        filter = zeros(length(x), 1);

        tt=0;

        while en<final
            tt = tt +1;
            [st,en]=split(x,en);
            if en>=final || en==-1 || st==-1
                break;
            end
            y=x_r(st:en);
            %hold on;
            [s,f]=myVAD(y, 0.0000001, 0.0000001);
    
            lengths(end+1)=f-s+1;
            [energies(end+1), maxs(end+1)] = signal_energy(y(s:f));
    
            s=s+st;
            f=f+st;
        %     q=y;
        %     q(s:f)=0;
        %     plot(y);
        %     plot(q);
    
            endpoints(end+1) = complex(s,f);
    
        %     if energies(end) < 0.25 && energies(end) > 0.001 && (f-s >= 1000)
        %         xx(s:f)=0;
        %         filter(s:f)=1;
        %     end
    
            % xx(s:f)=0;
            % hold off;
        end
        % 1-19/ 1-5
        mkdir('statistics')
        mkdir(['statistics/',fldr_name])
        save(['statistics/',fldr_name,transmitter],'endpoints','lengths','energies','maxs')
        
        sd=std(lengths);
        zs=(lengths-mean(lengths))./sd;
    
        num=1;
    
        for pi=1:length(energies)
            
            endpoint=endpoints(pi);
            s=real(endpoint);
            f=imag(endpoint);
            xx(s:f)=0;
            if pi < length(energies) && abs(zs(pi)) < 5 && maxs(pi) < 0.5 && energies(pi) < 0.25 && energies(pi) > 0.001 && pair_length(endpoints(pi)) >= 1000  && pair_length(endpoints(pi+1)) <= 2000 % && energies(i+1) > 0.4
                xx(s:f)=0;
                filter(s:f)=1;
    
                packet_log{end+1}=x(s:f);
                num=num+1;
    
            end
    
            if pi == length(energies) && abs(zs(pi)) < 5 && maxs(pi) < 0.5 && energies(pi) < 0.25 && energies(pi) > 0.001 && (f-s >= 1000)
                xx(s:f)=0;
                filter(s:f)=1;
    
                packet_log{end+1}=x(s:f);       
                num=num+1;
    
            end
    
        end
        
        mkdir('packets/')
        mkdir(['packets/',fldr_name])
        save(strcat('packets/',fldr_name,packet_log_filename), 'packet_log');
        
        downsample_fact = 100;
        
        close(fig)
        fig=figure(11);
        hold off;
        plot(x_r(1:downsample_fact:end));
        hold on;
        xxx = x_r(1:downsample_fact:end).*filter(1:downsample_fact:end);
        plot(xxx);
        hold off;
    
        mkdir('figs/')
        mkdir(['figs/',fldr_name])
%         savefig(fig,strcat('figs/',fldr_name,transmitter, '.fig'),'compact');
    
        
    
        fprintf(' %f\n',toc)

    end

    % figure;
    % plot(energies);



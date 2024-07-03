function pkt_stf_ltf_op = equalize_channel(pkt)
nht = wlanNonHTConfig;

pkt = resample(pkt,4,5);
pkt = [zeros(20,1); pkt];
strt_indx = wlanPacketDetect(pkt,'CBW20');
if isempty(strt_indx)
    pkt_stf_ltf_op=[];
    return
end 
if strt_indx+800> length(pkt)
    pkt_stf_ltf_op=[];
    return
end
pkt = pkt(strt_indx:strt_indx+800);
stf_ind = wlanFieldIndices(nht,'L-STF');
ltf_ind = wlanFieldIndices(nht,'L-LTF');
pkt_stf = pkt(stf_ind(1):stf_ind(2));

freqOffsetEst1 = wlanCoarseCFOEstimate(pkt_stf,'CBW20');
pkt = pkt.*exp(1j*(1:length(pkt))'/20e6*2*pi*-freqOffsetEst1 );
pkt_ltf = pkt(ltf_ind(1):ltf_ind(2));

freqOffsetEst2 = wlanFineCFOEstimate(pkt_ltf,'CBW20');

pkt = pkt.*exp(1j*(1:length(pkt))'/20e6*2*pi*-freqOffsetEst2 );

datIndx= [  39:64 2:27 ];




pkt_stf = pkt(stf_ind(1):stf_ind(2));
pkt_ltf = pkt(ltf_ind(1):ltf_ind(2));
demodSig = wlanLLTFDemodulate(pkt_ltf,nht);
nVar = helperNoiseEstimate(demodSig,nht.ChannelBandwidth,1);

est = wlanLLTFChannelEstimate(demodSig,nht);


pkt_stf_ltf = [pkt_stf; pkt_ltf];
pkt_stf_ltf_resh = reshape(pkt_stf_ltf,64,5);
pkt_stf_ltf_freq = fft(pkt_stf_ltf_resh,64);

pkt_stf_ltf_freq = pkt_stf_ltf_freq(datIndx,:);
h1=est;



pkt_stf_ltf_freq_eq = pkt_stf_ltf_freq.*conj(h1)./(conj(h1).*h1+nVar);
%pkt_stf_ltf_freq_eq = pkt_stf_ltf_freq./(h1);


pkt_stf_ltf_freq_eq_all = zeros(64,5);
pkt_stf_ltf_freq_eq_all(datIndx,:) = pkt_stf_ltf_freq_eq;
pkt_stf_ltf_eq = ifft(pkt_stf_ltf_freq_eq_all,64);
pkt_stf_ltf_eq = pkt_stf_ltf_eq(:);

pkt_stf_ltf_fo = pkt_stf_ltf_eq .*exp(1j*(1:length(pkt_stf_ltf_eq))'/20e6*2*pi*(freqOffsetEst1+freqOffsetEst2) );
pkt_stf_ltf_op = resample(pkt_stf_ltf_fo,5,4);
% pkt_ltf = pkt_stf_ltf_eq(ltf_ind(1):ltf_ind(2));
% demodSig = wlanLLTFDemodulate(pkt_ltf,nht);
% est = wlanLLTFChannelEstimate(demodSig,nht);
% h2=est;




























% function [pkt_stf_ltf_op] = equalize_channel(pkt)
% nht = wlanNonHTConfig;
% 
% pkt = resample(pkt,4,5);
% pkt = [zeros(20,1); pkt];
% strt_indx = wlanPacketDetect(pkt,'CBW20');
% if isempty(strt_indx)
%     pkt_stf_ltf_op=[];
%     return
% end 
% if strt_indx+800> length(pkt)
%     pkt_stf_ltf_op=[];
%     return
% end
% 
% X = pkt(strt_indx:end);
% % X = pkt;
% 
% 
% pkt = pkt(strt_indx:strt_indx+800);
% 
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 
% 
% % Generate the reference LTF sequence
% % The function wlanLLTF generates the L-LTF time domain signal for 802.11n
% ltfSequence = wlanLLTF(nht);
% stfSequence = wlanLSTF(nht);
% 
% % Perform correlation
% [correlationLTF, lagLTF] = xcorr(X, ltfSequence);
% [correlationSTF, lagSTF] = xcorr(X, stfSequence);
% 
% correlationLTF = abs(correlationLTF);
% correlationSTF = abs(correlationSTF);
% 
% % Let's only consider LTF for now
% % [m1, i1] = max(correlationSTF);
% % t1 = lagSTF(i1);
% 
% % figure;
% % hold on;
% % plot(lagSTF, correlationSTF);
% % plot(t1, 0, 'ro');
% % % xline(t1, "-");
% % hold off;
% % xlim([-6000, 6000])
% 
% 
% % % Find peaks in the correlation
% [~, locsLTF] = findpeaks(correlationLTF, 'MinPeakHeight', max(correlationLTF) * 0.8, 'MinPeakDistance', length(ltfSequence));
% [~, locsSTF] = findpeaks(correlationSTF, 'MinPeakHeight', max(correlationSTF) * 0.8, 'MinPeakDistance', length(stfSequence));
% 
% tLTF = lagLTF(locsLTF);
% tSTF = lagSTF(locsSTF);
% 
% 
% % return;
% 
% 
% 
% 
% 
% 
% 
% 
% 
% 
% 
% 
% 
% 
% 
% 
% 
% 
% 
% 
% 
% 
% 
% 
% 
% 
% stf_ind = wlanFieldIndices(nht,'L-STF');
% ltf_ind = wlanFieldIndices(nht,'L-LTF');
% pkt_stf = pkt(stf_ind(1):stf_ind(2));
% 
% freqOffsetEst1 = wlanCoarseCFOEstimate(pkt_stf,'CBW20');
% pkt = pkt.*exp(1j*(1:length(pkt))'/20e6*2*pi*-freqOffsetEst1 );
% pkt_ltf = pkt(ltf_ind(1):ltf_ind(2));
% 
% freqOffsetEst2 = wlanFineCFOEstimate(pkt_ltf,'CBW20');
% 
% pkt = pkt.*exp(1j*(1:length(pkt))'/20e6*2*pi*-freqOffsetEst2 );
% 
% datIndx= [  39:64 2:27 ];
% 
% 
% 
% 
% pkt_stf = pkt(stf_ind(1):stf_ind(2));
% pkt_ltf = pkt(ltf_ind(1):ltf_ind(2));
% demodSig = wlanLLTFDemodulate(pkt_ltf,nht);
% nVar = helperNoiseEstimate(demodSig,nht.ChannelBandwidth,1);
% 
% est = wlanLLTFChannelEstimate(demodSig,nht);
% 
% 
% pkt_stf_ltf = [pkt_stf; pkt_ltf];
% pkt_stf_ltf_resh = reshape(pkt_stf_ltf,64,5);
% pkt_stf_ltf_freq = fft(pkt_stf_ltf_resh,64);
% % Pick only the subcarriers that we care about (ignore null & pilot)
% pkt_stf_ltf_freq = pkt_stf_ltf_freq(datIndx,:);
% h1=est;
% 
% 
% 
% pkt_stf_ltf_freq_eq = pkt_stf_ltf_freq.*conj(h1)./(conj(h1).*h1+nVar);
% %pkt_stf_ltf_freq_eq = pkt_stf_ltf_freq./(h1);
% 
% 
% pkt_stf_ltf_freq_eq_all = zeros(64,5);
% pkt_stf_ltf_freq_eq_all(datIndx,:) = pkt_stf_ltf_freq_eq;
% pkt_stf_ltf_eq = ifft(pkt_stf_ltf_freq_eq_all,64);
% pkt_stf_ltf_eq = pkt_stf_ltf_eq(:);
% 
% pkt_stf_ltf_fo = pkt_stf_ltf_eq .*exp(1j*(1:length(pkt_stf_ltf_eq))'/20e6*2*pi*(freqOffsetEst1+freqOffsetEst2) );
% pkt_stf_ltf_op = resample(pkt_stf_ltf_fo,5,4);
% % pkt_ltf = pkt_stf_ltf_eq(ltf_ind(1):ltf_ind(2));
% % demodSig = wlanLLTFDemodulate(pkt_ltf,nht);
% % est = wlanLLTFChannelEstimate(demodSig,nht);
% % h2=est;

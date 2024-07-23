function [] = plot_recognized_frames(X, frame_bounds)
    figure;
    hold on;
    plot(real(X), 'black');
    for i = 1:length(frame_bounds)
        bounds = frame_bounds{i};

        frame_start = bounds(1);
        frame_end = bounds(2);
    
        plot(frame_start:frame_end, real(X(frame_start:frame_end)), 'green');
    end
    hold off;
end
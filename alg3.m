clear; clc;

X = [5 5; 3 6; 4 4; 5 3; 3 3; 1 8; 3 4; 4 5; 3 10; 6 6; 4 1; 3 5];

[P, idxP, stats] = owd_punkt_idealny(X);

disp('Punkty niezdominowane P(X):'); disp(P);
disp('Indeksy w X:'); disp(idxP');
fprintf('Porownania punktow (faza 2):      %d\n', stats.porPkt);
fprintf('Porownania wspolrzednych (faza 2): %d\n', stats.porWsp);
fprintf('Porownania przy sortowaniu:        %d\n', stats.porSort);
fprintf('Porownania punktow lacznie:        %.2f\n', stats.porPktRazem);
fprintf('Czas: %.6f s\n', stats.czas);

figure; hold on; grid on;
plot(X(:,1), X(:,2), 'bo', 'MarkerSize', 8);
plot(P(:,1), P(:,2), 'rd', 'MarkerSize', 10, 'MarkerFaceColor', 'r');
plot(min(X(:,1)), min(X(:,2)), 'k*', 'MarkerSize', 12);
legend('Zbior X', 'P(X)', 'Punkt idealny');
xlabel('Kryterium 1 (min)'); ylabel('Kryterium 2 (min)');
title('Metoda punktu idealnego');

function [P, idxP, stats] = owd_punkt_idealny(X)
    tic;
    n = size(X, 1);
    porPkt = 0; porWsp = 0;

    xmin = min(X, [], 1);                 
    d = sum((X - xmin).^2, 2);            
    [~, J, porSort] = merge_sort_cnt(d);  

    aktywny = true(n, 1);
    idxP = zeros(0, 1);

    for m = 1:n
        a = J(m);
        if ~aktywny(a), continue; end
        idxP(end+1, 1) = a;               
        aktywny(a) = false;
        for i = find(aktywny)'
            [dom, c] = dominuje(X(a, :), X(i, :));
            porPkt = porPkt + 1;
            porWsp = porWsp + c;
            if dom, aktywny(i) = false; end
        end
        if ~any(aktywny), break; end
    end

    P = X(idxP, :);
    stats.porPkt  = porPkt;
    stats.porWsp  = porWsp;
    stats.porSort = porSort;
    if porWsp > 0
        stats.porPktSort = porSort * porPkt / porWsp;
    else
        stats.porPktSort = 0;
    end
    stats.porPktRazem = stats.porPkt + stats.porPktSort;
    stats.czas = toc;
end

function [d, c] = dominuje(y, x)
    d = true; c = 0;
    for i = 1:numel(y)
        c = c + 1;
        if y(i) > x(i), d = false; return; end
    end
end

function [s, idx, c] = merge_sort_cnt(v)
    v = v(:); n = numel(v); idx = (1:n)'; c = 0;
    if n <= 1, s = v; return; end
    mid = floor(n / 2);
    [s1, i1, c1] = merge_sort_cnt(v(1:mid));
    [s2, i2, c2] = merge_sort_cnt(v(mid+1:end));
    i2 = i2 + mid; c = c1 + c2;
    s = zeros(n, 1); idx = zeros(n, 1);
    p = 1; q = 1; r = 1;
    while p <= numel(s1) && q <= numel(s2)
        c = c + 1;
        if s1(p) <= s2(q)
            s(r) = s1(p); idx(r) = i1(p); p = p + 1;
        else
            s(r) = s2(q); idx(r) = i2(q); q = q + 1;
        end
        r = r + 1;
    end
    s(r:end)   = [s1(p:end); s2(q:end)];
    idx(r:end) = [i1(p:end); i2(q:end)];
end
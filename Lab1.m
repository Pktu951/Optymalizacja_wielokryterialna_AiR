%% Julia Wiater Łukasz Mamczura Kacper Wójcik
clear; clc; close all;

X = [5 5; 3 6; 4 4; 5 3; 3 3; 1 8; 3 4; 4 5; 3 10; 6 6; 4 1; 3 5];

%% Obliczenia
[P1, s1] = no_filter(X);
[P2, s2] = filter_alg(X);
[P3, idxP, s3] = owd_punkt_idealny(X);

%% Wyniki w oknie polecen
fprintf('\nALGORYTM 1 - BEZ FILTRACJI\n');
disp('Punkty niezdominowane:'); disp(P1);
fprintf('Porownania punktow: %d\n', s1.porPkt);
fprintf('Porownania wspolrzednych: %d\n', s1.porWsp);
fprintf('Czas: %.6f s\n', s1.czas);

fprintf('\nALGORYTM 2 - Z FILTRACJA\n');
disp('Punkty niezdominowane:'); disp(P2);
fprintf('Porownania punktow: %d\n', s2.porPkt);
fprintf('Porownania wspolrzednych: %d\n', s2.porWsp);
fprintf('Czas: %.6f s\n', s2.czas);

fprintf('\nALGORYTM 3 - PUNKT IDEALNY\n');
disp('Punkty niezdominowane:'); disp(P3);
disp('Indeksy punktow w X:'); disp(idxP');
disp('Punkt idealny:'); disp(min(X, [], 1));
fprintf('Porownania punktow (faza 2): %d\n', s3.porPkt);
fprintf('Porownania wspolrzednych (faza 2): %d\n', s3.porWsp);
fprintf('Porownania przy sortowaniu: %d\n', s3.porSort);
fprintf('Szacowane porownania punktow lacznie: %.2f\n', s3.porPktRazem);
fprintf('Czas: %.6f s\n', s3.czas);

%% Wykresy zbiorow punktow (pierwsze dwa kryteria)
if size(X, 2) >= 2
    if size(X, 2) > 2
        fprintf('Uwaga: wykresy punktow pokazuja tylko pierwsze dwa kryteria.\n');
    end

    figure('Name', 'Punkty niezdominowane');
    P_lista = {P1, P2, P3};
    nazwy = {'1. Bez filtracji', '2. Z filtracja', '3. Punkt idealny'};

    for i = 1:3
        subplot(1, 3, i); hold on; grid on;
        plot(X(:,1), X(:,2), 'bo', 'MarkerSize', 8);
        P = P_lista{i};
        plot(P(:,1), P(:,2), 'rd', 'MarkerSize', 9, 'MarkerFaceColor', 'r');

        if i == 3
            xmin = min(X, [], 1);
            plot(xmin(1), xmin(2), 'k*', 'MarkerSize', 12);
            legend('Zbior X', 'P(X)', 'Punkt idealny', 'Location', 'best');
        else
            legend('Zbior X', 'P(X)', 'Location', 'best');
        end

        xlabel('Kryterium 1 (min)');
        ylabel('Kryterium 2 (min)');
        title(nazwy{i});
    end
end

% =========================================================
% ALGORYTM 1 - BEZ FILTRACJI
% =========================================================
function [P_X, stats] = no_filter(X)
    tic;
    n = size(X, 1);
    P_X = zeros(0, size(X, 2));
    active = true(n, 1);
    porPkt = 0; porWsp = 0;

    for i = 1:n
        if ~active(i), continue; end
        Y = X(i, :);
        fl = 0;

        for j = i+1:n
            if ~active(j), continue; end

            [wynik, c] = porownaj(Y, X(j, :));
            porPkt = porPkt + 1;
            porWsp = porWsp + c;

            if wynik == 1
                active(j) = false;
            elseif wynik == -1
                active(i) = false;
                Y = X(j, :);
                fl = 1;
            end
        end

        if ~ismember(Y, P_X, 'rows')
            P_X = [P_X; Y];
        end
        if fl == 0
            active(i) = false;
        end
    end

    stats.porPkt = porPkt;
    stats.porWsp = porWsp;
    stats.czas = toc;
end

% =========================================================
% ALGORYTM 2 - Z FILTRACJA
% =========================================================
function [P_X, stats] = filter_alg(X)
    tic;
    P_X = zeros(0, size(X, 2));
    porPkt = 0; porWsp = 0;

    while ~isempty(X)
        Y = X(1, :);
        X(1, :) = [];
        j = 1;

        while j <= size(X, 1)
            [wynik, c] = porownaj(Y, X(j, :));
            porPkt = porPkt + 1;
            porWsp = porWsp + c;

            if wynik == 1
                X(j, :) = [];
            elseif wynik == -1
                Y = X(j, :);
                X(j, :) = [];
                j = 1;
            elseif isequal(Y, X(j, :))
                X(j, :) = [];
            else
                j = j + 1;
            end
        end

        P_X = [P_X; Y];
        k = 1;

        while k <= size(X, 1)
            [wynik, c] = porownaj(Y, X(k, :));
            porPkt = porPkt + 1;
            porWsp = porWsp + c;
            if wynik == 1
                X(k, :) = [];
            else
                k = k + 1;
            end
        end
    end

    stats.porPkt = porPkt;
    stats.porWsp = porWsp;
    stats.czas = toc;
end

% =========================================================
% ALGORYTM 3 - PUNKT IDEALNY (jak w alg3.m)
% =========================================================
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
    stats.porPkt = porPkt;
    stats.porWsp = porWsp;
    stats.porSort = porSort;
    if porWsp > 0
        stats.porPktSort = porSort * porPkt / porWsp;
    else
        stats.porPktSort = 0;
    end
    stats.porPktRazem = stats.porPkt + stats.porPktSort;
    stats.czas = toc;
end

% Porownanie dwoch punktow: 1 = Y dominuje X, -1 = X dominuje Y,
% 0 = punkty nieporownywalne lub jednakowe.
function [wynik, c] = porownaj(Y, X)
    lepszy = false;
    gorszy = false;
    c = 0;

    for i = 1:numel(Y)
        c = c + 1;
        if Y(i) < X(i)
            lepszy = true;
        elseif Y(i) > X(i)
            gorszy = true;
        end
        if lepszy && gorszy, break; end
    end

    wynik = 0;
    if lepszy && ~gorszy
        wynik = 1;
    elseif gorszy && ~lepszy
        wynik = -1;
    end
end

% Sprawdzanie dominacji na potrzeby algorytmu 3.
function [d, c] = dominuje(y, x)
    d = true; c = 0;
    for i = 1:numel(y)
        c = c + 1;
        if y(i) > x(i), d = false; return; end
    end
end

% Sortowanie zliczajace porownania (oryginalny algorytm 3).
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
    s(r:end) = [s1(p:end); s2(q:end)];
    idx(r:end) = [i1(p:end); i2(q:end)];
end

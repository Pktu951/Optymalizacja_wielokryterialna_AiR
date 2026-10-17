function [P_X] = no_filter(X)

    n=size(X,1);
    P_X=zeros(0,size(X,2));

    active = true(n,1);

    for i=1:n
        
        if ~active(i)
            continue;
        end

        Y=X(i, :);
        fl=0;
    
        for j=i+1:n
            if ~active(j)
                continue;
            end

            if all(Y<=X(j,:)) && any(Y<X(j,:))
                active(j) = false;
            elseif all(X(j,:)<=Y) && any(X(j,:) < Y)
                active(i)=false;
                Y=X(j,:);
                fl=1;
            end
        end

    if ~ismember(Y, P_X, 'rows')
            P_X = [P_X; Y];
        end

    if fl==0
        active(i)=false;
    end
end
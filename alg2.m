function [P_X] = filter_alg(X)

    n=size(X,1);
    P_X=zeros(0,n);

    while ~isempty(X)
        Y=X(1, :);
        X(1,:)=[];

        j = 1;
    
        while j <= size(X, 1)
            if all(Y<=X(j,:)) && any(Y < X(j,:))
                X(j,:)=[];
            elseif all(X(j,:)<=Y) && any(X(j,:) < Y)
                Y=X(j,:);
                X(j,:) = [];
                j = 1;
            elseif all(X(j,:) == Y)
                X(j,:) = [];
            else
                j = j + 1;
            end
        end

        P_X=[P_X;Y];
    
        k = 1;

        while k <= size(X, 1) 
            if all(X(k,:)>=Y) && any(Y < X(k,:))
                X(k,:) = [];
            else
                k = k+1;
            end
        end
    end

end
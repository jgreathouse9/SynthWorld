% Adapted from the ADH paper on SC 
% Using augmented data
% Main idea: add l1 penalty to the loss function 

clear all;
diary main;
%rng('default')

%% Get Data
cd '/Users/jaumevives/Desktop/Projects/Model Selection SC/_code_paper_version/empirical application/sparse'
%load MLAB_data.txt;
%data = MLAB_data;
data = readtable('augmented_cali.csv');
Xdata = readtable('X_redux.csv');

%% Define Matrices for Predictors
% from 8 to 39 are the Ys
% 40 and 41 are state and year

num_pred = 41; %width(Xdata);

% X0 : 7 X 38 matrix (7 smoking predictors for 38 control states)
X0 = transpose(Xdata{1:38,[2:num_pred]});

% X1 : 10 X 1 matrix (10 crime predictors for 1 treated states)
X1 = transpose(Xdata{39,[2:num_pred]});

% Normalization (probably could be done more elegantly)
bigdata = [X0,X1];
divisor = std(bigdata');
scamatrix = (bigdata' * diag(( 1./(divisor) * eye(size(bigdata,1))) ))';
X0sca = scamatrix([1:size(X0,1)],[1:size(X0,2)]);
X1sca = scamatrix(1:size(X1,1),[size(scamatrix,2)]);
X0 = X0sca;
X1 = X1sca;
clear divisor X0sca X1sca scamatrix bigdata;

%% Define Matrices for Outcome Data
% Y0 : 31 X 38 matrix (31 years of smoking data for 38 control states)
Y0 = transpose(data{1:38, 9:39});
% Y1 : 31 X 1 matrix (31 years of smoking data for 1 treated state)
Y1 = transpose(data{39, 9:39});

% Now pick Z matrices, i.e. the pretreatment period
% over which the loss function should be minmized
% Here we pick Z to go from 1970 to 1988 

% Validation and Training periods
Te = 14;
T = 19;

% training period
Z0t = Y0([1:Te],1:38);
Z1t = Y1([1:Te],1);

% validation period
Z0v = Y0([Te+1:T],1:38);
Z1v = Y1([Te+1:T],1);


% Z0 : 19 X 38 matrix (31 years of pre-treatment smoking data for 38 control states)
Z0 = Y0([1:19],1:38);
% Z1 : 19 X 1 matrix (31 years of pre-treatment smoking data for 1 treated state)
Z1 = Y1([1:19],1);

% hack to see how much is the split contributing
Z0v = Z0;
Z1v = Z1;

Z0t = Z0;
Z1t = Z1;

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Now we implement Optimization

% Check and maybe adjust optimization settings if necessary
options = optimoptions('fmincon', 'Display', 'off');

% Get Starting Values 
s = std([X1 X0]')';
s2 = s; s2(1)=[];
s1 = s(1);
v20 =((s1./s2).^2);
v20 = v20/width(Xdata); %[1; v20]/width(Xdata);

% Hyperparameter tuning
% Lambda grid
deltaLambda = 0.01;
firstLambda = 0.01:deltaLambda:0.3;
maxLambda = 20;
Lambda = firstLambda;
margin = 25;
dlambda = margin*deltaLambda;
Lnum = 50;
deltaLambda = 0.000001;
Lambda = [0, logspace(-4, 0, Lnum)];

% Iterate over lambda grid
j = 1;
fmins = [];
errs = [];
minfmin = Inf;
minerr = Inf;
optlambda = 0;
optv = [1; v20];
Vs = [];

while j <= length(Lambda)
    lambda = Lambda(j);
    
    [v2,fminv,exitflag] = fmincon('loss_function',v20,[],[],[], [],...
       zeros(size(X1)),[],[],options,X1,X0,Z1t,Z0t, lambda);
    
    v = [1; v2];
    
    % store the Vs
    Vs = [Vs; v];
    
    % collect the results
    fmins = [fmins; fminv];
    
    % evaluate at the validation set
    err = mse(v2,X1,X0,Z1v,Z0v);
    errs = [errs; err];
    
    % save 0
    if j==1
        zerov = v;
    end
    
    % Update min lambda
    if err < minerr
        minerr = err;
        optlambda = lambda;
        optv = v;
    end
    j = j + 1;
    % Increase grid size if last lambda optimal
    %
    %if j > length(Lambda)         
    %    if (((round(lambda-optlambda,5)<round(dlambda,5))...
    %          && (round(lambda+deltaLambda,5)<round(maxLambda,5))))
    %      Lambda = [Lambda lambda+(deltaLambda:deltaLambda:dlambda)];
    %    end
    %end
end

% train the model with the optimal lambda chosen
%options = optimoptions('fmincon', 'Display', 'off');
%[v2,fminv,exitflag] = fmincon('loss_function',v20,[],[],[], [],...
%       zeros(size(X1)),[],[],options,X1,X0,Z1,Z0, optlambda);
   
% save the v weights
csvwrite("optv_sparseSC.csv", optv);


% Now recover W-weights
D = diag(optv);
H = X0'*D*X0;
f = - X1'*D*X0;
options = optimset('quadprog');
[w,fval,e]=quadprog(H,f,[],[],ones(1,38),1,zeros(38,1),ones(38,1),[],options);
w = abs(w); 

% W-weights
w

%%%%%%%%%%%%%%%%%%%%%%%%%%%%
figure;
years = [1970:2000]'; 
plot(years,Y1,'-k', years,Y0*w,'--k','LineWidth',.7);
axis([1970 2000 0 140]);

% Get the treatment effect
gaps = Y1 - Y0*w;
tau = mean(gaps([T+1:end]));
tau


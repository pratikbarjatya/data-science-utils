from data_science_utils import dataframe as utils

import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import matplotlib as mplt
import matplotlib.pyplot as plt
from sklearn.preprocessing import RobustScaler
from sklearn.preprocessing import MinMaxScaler
import matplotlib.ticker as ticker
from sklearn.metrics import mean_squared_error


def scatter_plot_exclude_outliers(f_name,predicted_column,df,title=None,percentile=[0.01,0.99],logy=False,logx=False):
    df = utils.filter_dataframe_percentile(df,{f_name:percentile,predicted_column:percentile})
    df.plot.scatter(x=f_name, y=predicted_column,title=title,logy=logy,logx=logx)
    plt.figure();
    plt.show();


def plot_numeric_feature(f_name,predicted_column,df):
    figsize = mplt.rcParams['figure.figsize']
    mplt.rcParams['figure.figsize'] = (12,8)
    if(len(df)==0):
        print("Empty Dataframe - No plots possible")
        return


    df["log_%s" %f_name] = np.log(df[f_name]+1)
    df["square_root_%s" %f_name] = df[f_name]**0.5
    df["square_%s" %f_name] = df[f_name]**2
    df["cube_%s" %f_name] = df[f_name]**3

    scatter_plot_exclude_outliers(f_name, predicted_column,df,title="%s vs %s" %(predicted_column,f_name),logy=False)
    scatter_plot_exclude_outliers(f_name, predicted_column,df,title="Log %s vs %s" %(predicted_column,f_name),logy=True)
    scatter_plot_exclude_outliers("log_%s" %f_name, predicted_column,df,title="%s vs Log %s"%(predicted_column,f_name))
    scatter_plot_exclude_outliers("square_root_%s" %f_name, predicted_column,df,title="%s vs square_root %s"%(predicted_column,f_name))
    scatter_plot_exclude_outliers("square_%s" %f_name, predicted_column,df,title="%s vs square %s"%(predicted_column,f_name))
    scatter_plot_exclude_outliers("cube_%s" %f_name, predicted_column,df,title="%s vs cube %s"%(predicted_column,f_name))
    mplt.rcParams['figure.figsize'] = figsize
    plt.figure();
    plt.show();

def plot_numeric_features_filtered(f_name,predicted_column,df,filter_columns,strategy=None):
    colnames = [f_name]
    if strategy is None:
        colnames = [f_name]
    elif strategy=='prefix':
        colnames = df.columns[pd.Series(df.columns).str.startswith(f_name)]
    elif strategy=='suffix':
        colnames = df.columns[pd.Series(df.columns).str.endswith(f_name)]
    print("------Histograms for Distribution------")
    mplt.rcParams['figure.figsize'] = (6,4)
    for colname in colnames:
        df.hist(column=colname, bins=20)
    plt.show();
    df = utils.filter_dataframe(df,filter_columns)
    print("------Feature vs Predicted Column------")
    for colname in colnames:
        plot_numeric_feature(colname,predicted_column,df)


def plot_ts(df_test, columns=[], time_col='week', freq='7D', xtick_interval=None,figsize=(24,8)):
    df_preds = df_test.sort_values([time_col])
    idx = pd.date_range(df_test[time_col].min(), df_test[time_col].max(), freq=freq)
    df_preds.set_index(time_col, inplace=True)
    scaler = MinMaxScaler()
    df_preds[columns] = scaler.fit_transform(df_preds[columns])
    fg = plt.rcParams["figure.figsize"]
    plt.rcParams["figure.figsize"] = figsize
    fig, ax1 = plt.subplots()

    handles = []
    for column in columns:
        tsSparseActual = df_preds[column]
        tsActual = tsSparseActual.reindex(idx, fill_value=0)
        p1, = plt.plot(tsActual.index, tsActual, linestyle='--', marker='o', label=column)
        handles.append(p1)
    # showing right number of x labels
    if xtick_interval is None:
        xtick_interval = np.ceil(len(df_preds) / (fg[1] * 4.0))
    fig.autofmt_xdate(rotation=60, bottom=0.2)
    for n, label in enumerate(ax1.xaxis.get_ticklabels()):
        if n % xtick_interval != 0:
            label.set_visible(False)

    plt.legend(handles=handles)
    plt.show()
    plt.rcParams["figure.figsize"] = fg


def plot_ts_single_column(df_test, time_col,freq='7D', target='target', ewma_diff_plot=True, ewma_range=3,ewma_shift=0,
                          figsize=(24, 8)):
    idx = pd.date_range(df_test[time_col].min(), df_test[time_col].max(), freq=freq)
    df_preds = df_test.sort_values([time_col])
    df_preds.set_index(time_col, inplace=True)
    fg = plt.rcParams["figure.figsize"]
    plt.rcParams["figure.figsize"] = figsize
    tsSparseActual = df_preds[target]
    tsActual = tsSparseActual.reindex(idx, fill_value=1)
    df_preds['ewma'] = pd.ewma(tsActual.shift(ewma_shift).fillna(tsActual.min()), span=ewma_range)
    tsSparse = df_preds['ewma']
    ts = tsSparse.reindex(idx, fill_value=1)
    tsDiff = (tsActual - ts) / ts
    fig, ax1 = plt.subplots()
    fig.autofmt_xdate(rotation=60, bottom=0.2)
    p1, = plt.plot(tsActual.index, tsActual, linestyle='--', marker='o', label=target)

    handles = [p1]
    if ewma_diff_plot:
        p2, = plt.plot(ts.index, ts, linestyle='-.', marker='o', label="EWMA")
        handles = [p1, p2]
        plt.legend(handles=handles)
        plt.show()
        p3, = plt.plot(tsDiff.index, tsDiff, linestyle='-', marker='o', label="Diff")
        plt.legend(handles=[p3])
        plt.show()
    else:
        plt.legend(handles=handles)
        plt.show()
    plt.rcParams["figure.figsize"] = fg
    return pd.DataFrame({"target": tsActual, "EWMA": ts, "Diff": tsDiff, time_col: df_preds.index})


def analyze_ts_results(test_true, test_pred, train_true=[], train_pred=[], timestamps=[], aep_line=20,
                       sample_percentile=80, plot=True, plot_error=False, xtick_interval=None, figsize=(24, 8)):
    assert len(test_true) == len(test_pred)
    assert len(train_true) >= len(train_pred)

    train_ts = None
    test_ts = None
    if len(timestamps) == 0:
        timestamps = np.arange(0, len(test_true) + len(train_true))

    assert len(test_true) + len(train_true) == len(timestamps)
    train_ts = timestamps[:len(train_true)]
    test_ts = timestamps[len(train_true):]
    import matplotlib.ticker as ticker

    test_true = np.array(test_true)
    test_pred = np.array(test_pred)
    train_true = np.array(train_true)
    train_pred = np.array(train_pred)

    assert np.all(test_true >= 0)
    assert np.all(train_true >= 0)

    errors = np.absolute(test_true - test_pred)
    mae = np.mean(errors)

    #
    rmse = mean_squared_error(test_true, test_pred) ** (.5)
    train_rmse = np.nan
    if len(train_true) == len(train_pred):
        train_rmse = mean_squared_error(train_true, train_pred) ** (.5)

    # scaler = MinMaxScaler()
    # all_samples = np.concatenate((test_true,test_pred,train_true,train_pred))
    # scaler.fit(all_samples.reshape(-1, 1))
    # tt,tp = scaler.transform(test_true.reshape(-1, 1)).flatten(),scaler.transform(test_pred.reshape(-1, 1)).flatten()
    tt, tp = test_true, test_pred
    tt[tt <= 1e-8] = 1
    tp[tp <= 1e-8] = 1
    absolute_percent_errors_test = 100 * np.abs(tt - tp) / tt
    #
    mape = np.mean(absolute_percent_errors_test)

    train_mape = np.nan
    if len(train_true) == len(train_pred):
        # tt,tp = scaler.transform(train_true.reshape(-1, 1)).flatten(),scaler.transform(train_pred.reshape(-1, 1)).flatten()
        tt, tp = train_true, train_pred
        tt[tt <= 1e-8] = 1
        tp[tp <= 1e-8] = 1
        train_mape = np.mean(100 * np.abs(tt - tp) / tt)

    length = len(test_true)
    below_percents = [0.1, 0.5, 1, 5, 10, 15, 20, 25, 30, 35, 40]
    below_percents.append(aep_line)
    below_percents = sorted(set(below_percents))
    error_count_list = list()
    percent_count_list = list()
    description_list = list()
    for p in below_percents:
        count = np.sum(absolute_percent_errors_test <= p)
        error_count_list.append(count)
        pc = count * 100.0 / length
        percent_count_list.append(pc)
        description_list.append("samples with error below %s %% = %.3f%%" % (p, pc))
    error_percent_summary = pd.DataFrame({"error_percent": below_percents, "samples_with_error_lteq": error_count_list,
                                          "sample_percentage_with_error_lteq": percent_count_list,
                                          "description": description_list})

    # 80% samples have error below or equal to x%
    description_list = list()
    percent_list = list()
    sample_percents = [99.9, 99.5, 99, 95, 90, 85, 80, 75, 70, 65, 60, 50]
    sample_percents.append(sample_percentile)
    sample_percents = sorted(set(sample_percents))
    for sp in sample_percents:
        pct = np.percentile(absolute_percent_errors_test, sp)
        percent_list.append(pct)
        description_list.append("%s%% samples have error <= %.3f%%" % (sp, pct))
    sample_summary = pd.DataFrame(
        {"sample_percentage": sample_percents, "error_percentage": percent_list, "description": description_list})

    #
    aep_metric = error_percent_summary[error_percent_summary["error_percent"] == aep_line][
        "sample_percentage_with_error_lteq"].values[0]

    #
    sample_percentile_metric = \
    sample_summary[sample_summary["sample_percentage"] == sample_percentile]["error_percentage"].values[0]

    # This tells us averagely how much variation from one sample to another.
    # A sine curve with good sampling rate will have low value
    # A sine curve with bad sampling rate will have higher value since percent changes will be higher between consecutive samples
    td = np.diff(test_true)
    tp = test_true[:len(test_true) - 1]
    idx = np.all([(td == 0), (tp == 0)], axis=0) == False
    td = td[idx]
    tp = tp[idx]
    tp[np.all([(tp <= 1e-6), (tp >= -1e-6)], axis=0)] = 1
    mean_absolute_percent_change = 100 * np.mean(np.abs(td / tp))

    testMean = np.mean(test_true)

    #
    perc_error = (rmse * 100.0) / testMean

    padding = np.full((len(train_true)), np.nan)

    if plot:
        fg = plt.rcParams["figure.figsize"]
        plt.rcParams["figure.figsize"] = figsize
        fig, ax1 = plt.subplots()

        if len(train_true) > 0:
            ax1.plot(train_ts, train_true, marker='o', linestyle=':', color='lightgrey', label='Train True')
        if len(train_pred) > 0:
            ax1.plot(train_ts, train_pred, marker='d', color='lightblue', label='Train Predictions')

        ax1.plot(timestamps, np.concatenate((padding, test_true)), marker='o', linestyle=':', color='grey',
                 label='Test True')
        ax1.axhline(y=testMean, linestyle='--', color='brown', label='Test Mean')
        ax1.plot(timestamps, np.concatenate((padding, test_pred)), marker='d', color='blue', label='Prediction')
        if plot_error:
            ax1.plot(timestamps, np.concatenate((padding, errors)), color='red', label='Error')
        ax1.axhline(y=mae, linestyle='--', color='lightsalmon', label='Mean Absolute Error')
        ax1.axhline(y=rmse, linestyle='--', color='green', label='RMSE')
        ax1.legend(loc=2)

        # showing right number of x labels
        if xtick_interval is None:
            xtick_interval = np.ceil(len(timestamps) / (fg[1] * 4.0))
        fig.autofmt_xdate(rotation=60, bottom=0.2)
        for n, label in enumerate(ax1.xaxis.get_ticklabels()):
            if n % xtick_interval != 0:
                label.set_visible(False)

        str0 = "Data Stats: Test samples= %i, for test mean %.3f, Mean Absolute Percent change across consecutive samples: %.3f%%\n" % (
        len(test_true), testMean, mean_absolute_percent_change)
        str1 = 'RMSE of %.3f giving RMSE error %% of +/- %.3f%%, Mean absolute error of %.3f and Mean Absolute percent error of %.3f' % (
        rmse, perc_error, mae, mape)
        str2 = "samples with error below %s %% = %.3f%%, " % (
        aep_line, aep_metric) + "%s%% samples have error <= %.3f%%" % (sample_percentile, sample_percentile_metric)
        str3 = "\n"
        if len(train_true) == len(train_pred):
            str3 = "Training RMSE = %.3f, Training Mean Absolute percent error = %.3f\n" % (train_rmse, train_mape)
        plt.title(str0 + str3 + str1 + "\n" + str2)
        fig.tight_layout()
        plt.show()
        plt.rcParams["figure.figsize"] = fg
    result = {"mean_absolute_percent_change": mean_absolute_percent_change, "rmse": rmse, "perc_error": perc_error,
              "mae": mae, "mape": mape, "aep": aep_metric, "sample_percentile": sample_percentile_metric,
              "error_percent_summary": error_percent_summary, "sample_summary": sample_summary}
    return result


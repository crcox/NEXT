import json
import numpy
import numpy.random
from datetime import datetime
from datetime import timedelta
from next.utils import utils
from next.dashboard.AppDashboard import AppDashboard

# import next.database_client.DatabaseAPIHTTP as db
# import next.logging_client.LoggerHTTP as ell

class PoolBasedTripletMDSDashboard(AppDashboard):

    def __init__(self,db,ell):
        AppDashboard.__init__(self,db,ell)

    def get_app_supported_stats(self):
        """
        Returns a list of dictionaries describing the identifier (stat_id) and 
        necessary params inputs to be used when calling getStats

        Expected output (list of dicts, each with fields):
            (string) stat_id : the identiifer of the statistic
            (string) description : docstring of describing outputs
            (list of string) necessary_params : list where each string describes the type of param input like 'alg_label' or 'task'
        """
        stat_list = self.get_supported_stats()

        stat = {}
        stat['stat_id'] = 'test_error_multiline_plot'
        stat['description'] = self.test_error_multiline_plot.__doc__
        stat['necessary_params'] = []
        stat_list.append(stat)

        stat = {}
        stat['stat_id'] = 'most_current_embedding'
        stat['description'] = self.most_current_embedding.__doc__
        stat['necessary_params'] = ['alg_label']
        stat_list.append(stat)

        return stat_list
        
    def test_error_multiline_plot(self,app_id,exp_uid):
        """
        Description: Returns multiline plot where there is a one-to-one mapping lines to 
        algorithms and each line indicates the error on the validation set with respect to number of reported answers

        Expected input:
          None

        Expected output (in dict):
          (dict) MPLD3 plot dictionary
        """

        # get list of algorithms associated with project
        alg_list,didSucceed,message = self.db.get(app_id+':experiments',exp_uid,'alg_list')

        for algorithm in alg_list:
            test_alg_label = algorithm['test_alg_label']

        predict_id = 'get_queries'
        params = {'alg_label':test_alg_label}
        predict_args_dict = {'predict_id':predict_id,'params':params}
        predict_args_json = json.dumps(predict_args_dict)
        next_app = utils.get_app(app_id)
        args_out_json,didSucceed,message = next_app.predict(exp_uid, predict_args_json, self.db, self.ell)
        predict_args_dict = json.loads(args_out_json)
        test_S = predict_args_dict['args']['queries']

        x_min = numpy.float('inf')
        x_max = -numpy.float('inf')
        y_min = numpy.float('inf')
        y_max = -numpy.float('inf')
        list_of_alg_dicts = []

        for algorithm in alg_list:
            alg_id = algorithm['alg_id']
            alg_uid = algorithm['alg_uid']
            alg_label = algorithm['alg_label']

            list_of_log_dict,didSucceed,message = self.ell.get_logs_with_filter(app_id+':ALG-EVALUATION',{'alg_uid':alg_uid})
            list_of_log_dict = sorted(list_of_log_dict, key=lambda item: utils.str2datetime(item['timestamp']) )

            x = []
            y = []
            for item in list_of_log_dict:
                num_reported_answers = item['num_reported_answers']
                Xd = item['Xd']

                err = 0.5
                if len(test_S)>0:
                    # compute error rate
                    number_correct = 0.
                    for q in test_S:
                        i,j,k = q
                        score =  numpy.dot(Xd[j],Xd[j]) -2*numpy.dot(Xd[j],Xd[k]) + 2*numpy.dot(Xd[i],Xd[k]) - numpy.dot(Xd[i],Xd[i])
                        if score > 0:
                            number_correct += 1.0

                    accuracy = number_correct/len(test_S)
                    err = 1.0-accuracy

                x.append(num_reported_answers)
                y.append(err)

        
            alg_dict = {}
            alg_dict['legend_label'] = alg_label
            alg_dict['x'] = x
            alg_dict['y'] = y
            try:
                x_min = min(x_min,min(x))
                x_max = max(x_max,max(x))
                y_min = min(y_min,min(y))
                y_max = max(y_max,max(y))
            except:
                pass

            list_of_alg_dicts.append(alg_dict)

        import matplotlib.pyplot as plt
        import mpld3
        fig, ax = plt.subplots(subplot_kw=dict(axisbg='#EEEEEE'))
        for alg_dict in list_of_alg_dicts:
            ax.plot(alg_dict['x'],alg_dict['y'],label=alg_dict['legend_label'])
        ax.set_xlabel('Number of answered triplets')
        ax.set_ylabel('Error on hold-out set')
        ax.set_xlim([x_min,x_max])
        ax.set_ylim([y_min,y_max])
        ax.grid(color='white', linestyle='solid')
        ax.set_title('Triplet Test Error', size=14)
        legend = ax.legend(loc=2,ncol=3,mode="expand")
        for label in legend.get_texts():
          label.set_fontsize('small')
        plot_dict = mpld3.fig_to_dict(fig)
        plt.close()

        return plot_dict


    def most_current_embedding(self,app_id,exp_uid,alg_label):
        """
        Description: Returns embedding in the form of a list of dictionaries, which is conveneint for downstream applications

        Expected input:
          (string) alg_label : must be a valid alg_label contained in alg_list list of dicts 

        Expected output (in dict):
          plot_type : 'scatter2d_noaxis'
          (float) x_min : minimum x-value to display in viewing box
          (float) x_max : maximum x-value to display in viewing box
          (float) y_min : minimum y-value to display in viewing box
          (float) y_max : maximum y-value to display in viewing box
          (list of dicts with fields) data : 
            (int) index : index of target
            (float) x : x-value of target
            (float) y : y-value of target
        """

        predict_id = 'get_embedding'
        params = {'alg_label':alg_label}
        predict_args_dict = {'predict_id':predict_id,'params':params}
        predict_args_json = json.dumps(predict_args_dict)
        next_app = utils.get_app(app_id)
        args_out_json,didSucceed,message = next_app.predict(exp_uid, predict_args_json, self.db, self.ell)
        predict_args_dict = json.loads(args_out_json)
        item = predict_args_dict['args']

        embedding = item['Xd']

        data = []
        x_min = numpy.float('inf')
        x_max = -numpy.float('inf')
        y_min = numpy.float('inf')
        y_max = -numpy.float('inf')
        for idx,target in enumerate(embedding):

            target_dict = {}
            target_dict['index'] = idx
            target_dict['x'] = target[0] # this is what will actually be plotted, 
            try:
                target_dict['y'] = target[1] # takes first two components, (could be replaced by PCA)
            except:
                target_dict['y'] = 0.
            target_dict['darray'] = target

            x_min = min(x_min,target[0])
            x_max = max(x_max,target[0])
            y_min = min(y_min,target[1])
            y_max = max(y_max,target[1])

            data.append(target_dict)
    
        return_dict = {}
        return_dict['timestamp'] = item['timestamp']
        return_dict['x_min'] = x_min
        return_dict['x_max'] = x_max
        return_dict['y_min'] = y_min
        return_dict['y_max'] = y_max
        return_dict['data'] = data
        return_dict['plot_type'] = 'scatter2d_noaxis'

        return return_dict






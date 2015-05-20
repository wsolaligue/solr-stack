from resource_management import *
from subprocess import call
from resource_management.core.logger import Logger

class Master(Script):
    
  def parse_template(self):
    import params

    File(format("{solr_dir}/latest/bin/solr.in.sh"),
         content=Template("solr.in.sh.j2"),
         owner=params.solr_user
    )
    
  # Call setup.sh to install the service
  def install(self, env):
  
    # Install packages listed in metainfo.xml
    self.install_packages(env)
    self.configure(env)
    
    # import properties defined in -config.xml file from params class
    import params
    
    find_cmd = 'find ' + params.stack_dir + ' -iname "*.sh" | xargs chmod +x'
    
    Logger.info("Execute: " + find_cmd) 

    # Ensure the shell scripts in the services dir are executable 
    Execute(find_cmd)
        
    # form command to invoke setup.sh with its arguments and execute it
    if params.os_type == "ubuntu":
        cmd = params.stack_dir + '/scripts/setup.sh ' + params.solr_package_name + ' ' + params.solr_deb_file + ' ' + params.solr_installer_folder_location + ' ' + params.os_type + ' ' + params.stack_log
    else:
        cmd = params.stack_dir + '/scripts/setup.sh ' + params.solr_package_name + ' ' + params.solr_rpm_file + ' ' + params.solr_installer_folder_location + ' ' + params.os_type + ' ' + params.stack_log
    
    Logger.info("Execute: " + cmd) 
        
    Execute(cmd)
    
    if params.enable_ssl:
        self.parse_template()


  def configure(self, env):
    import params
    env.set_params(params)
    
  def check_zookeeper_status(self):
    import params
    cmd = params.stack_dir + '/scripts/check_zk_status.sh ' + params.zookeeper_directory + " " + params.zk_config_dir + " " + params.solr_user + " " + params.zk_cli_shell + " " + params.zk_node1 + " " + params.zk_client_port + " >> " + params.stack_log
    
    Logger.info("Execute: " + cmd) 
    
    Execute(cmd)
    
  def add_support_hdfs(self):
    import params
    
    hdfs_dir = params.hdfs_dir
    hadoop_bin_dir = params.hadoop_bin_dir
    hadoop_conf_dir = params.hadoop_conf_dir
            
    safemode_command = "dfsadmin -safemode get | grep OFF"
    create_dir_cmd = format("fs -mkdir {hdfs_dir}")
    chmod_command = format("fs -chmod 777 {hdfs_dir}")
    test_dir_exists = as_user(format("{hadoop_bin_dir}/hadoop --config {hadoop_conf_dir} fs -test -e {hdfs_dir}"), params.hdfs_user)
            
    ExecuteHadoop(safemode_command,
                  user=params.hdfs_user,
                  logoutput=True,
                  conf_dir=params.hadoop_conf_dir,
                  try_sleep=3,
                  tries=20,
                  bin_dir=params.hadoop_bin_dir
                  )
    ExecuteHadoop(create_dir_cmd,
                  user=params.hdfs_user,
                  logoutput=True,
                  not_if=test_dir_exists,
                  conf_dir=params.hadoop_conf_dir,
                  try_sleep=3,
                  tries=5,
                  bin_dir=params.hadoop_bin_dir
                  )
    ExecuteHadoop(chmod_command,
                  user=params.hdfs_user,
                  logoutput=True,
                  conf_dir=params.hadoop_conf_dir,
                  try_sleep=3,
                  tries=5,
                  bin_dir=params.hadoop_bin_dir
                  )
        
  def enable_ssl(self):
    import params
    
    cmd = params.stack_dir + '/scripts/enable_ssl.sh ' + params.solr_dir + ' ' + params.zk_node1 + " " + params.zk_client_port + " " + params.zookeeper_directory + " >> " + params.stack_log

    Logger.info("Execute: " + cmd)
    
    Execute(cmd)

  # Call start.sh to start the service
  def start(self, env):

    # import properties defined in -config.xml file from params class
    import params

    # import status properties defined in -env.xml file from status_params class
    import status_params
    
    # Ensure the shell scripts in the services dir are executable 
    Execute('find ' + params.stack_dir + ' -iname "*.sh" | xargs chmod +x')
    
    if params.solr_cloudmode:
        self.check_zookeeper_status()
        
    if params.enable_ssl:
        self.enable_ssl()
        
    if params.solr_hdfs_enable:
        self.add_support_hdfs()
        
    map_custom_properties = params.map_custom_properties
    custom_length = len(params.map_custom_properties)
    custom_command = ""
    
    if custom_length > 0:
        for key in map_custom_properties:
            value = map_custom_properties[key]
            if key.startswith("-D"):
                custom_command += str(key) + "=" + str(value) + " "
            else:
                custom_command += str(key) + " " + str(value) + " "
    
    # form command to invoke start.sh with its arguments and execute it
    cmd = params.stack_dir + "/scripts/start.sh " + params.solr_dir + " " + " " + status_params.stack_pidfile + " " + params.zookeeper_hosts + " " + params.zookeeper_directory + " " + params.solr_port + " " + str(params.solr_cloudmode) + " " + params.fs_default_name + " " + params.hdfs_dir + " " + params.solr_memory + " " + str(params.solr_hdfs_enable) + " '" + custom_command + "' " + params.stack_log + " >> " + params.stack_log
    Logger.info("Execute: " + cmd)
    
    Execute(cmd)

  # Called to stop the service using the pidfile
  def stop(self, env):
      
    # import properties defined in -config.xml file from params class
    import params
    
    import status_params
    
    cmd = params.stack_dir + '/scripts/stop.sh ' + params.solr_dir + ' ' + params.solr_port + ' ' + status_params.stack_pidfile + ' >> ' + params.stack_log
    
    Logger.info("Execute: " + cmd) 
    
    Execute(cmd)

      	
  # Called to get status of the service using the pidfile
  def status(self, env):
  
    # import status properties defined in -env.xml file from status_params class
    import status_params
        
    env.set_params(status_params)  
    
    # use built-in method to check status using pidfile
    check_process_status(status_params.stack_pidfile)  

if __name__ == "__main__":
  Master().execute()

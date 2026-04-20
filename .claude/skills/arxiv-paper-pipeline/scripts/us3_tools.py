from ufile import config, filemanager
from ufile import multipartuploadufile
import json
import io

class US3Client(object):

    def __init__(self):
        # 密钥可在https://console.ucloud.cn/uapi/apikey中获取
        self.public_key = "TOKEN_549ff4f7-65aa-423e-91a5-d57051e05769"  # 账户公钥
        self.private_key = "7743efd5-e0fb-4e86-be17-440f7de32bc4"  # 账户私钥

        self.bucket = "omni-data-crafter-s3"  # 空间名称

        external_endpoint = ".cn-sh2.ufileos.com"
        intranet_endpoint = ".internal-cn-sh2-01.ufileos.com"
        active_endpoint = intranet_endpoint
        config.set_default(connection_timeout=360)

        # 以下两项如果不设置，则默认设为'.cn-bj.ufileos.com'，如果上传、下载文件的bucket所在地域不在北京，请务必设置以下两项。
        # 设置上传host后缀,外网可用后缀形如 .cn-bj.ufileos.com（cn-bj为北京地区，其他地区具体后缀可见控制台：对象存储-单地域空间管理-存储空间域名）
        upload_suffix = active_endpoint
        config.set_default(uploadsuffix=upload_suffix)
        # 设置下载host后缀，普通下载后缀即上传后缀，CDN下载后缀为 .ufile.ucloud.com.cn
        download_suffix = active_endpoint
        config.set_default(downloadsuffix=download_suffix)

        self.ufile_handler = filemanager.FileManager(self.public_key, self.private_key, upload_suffix, download_suffix)
        self.multipartuploadufile_handler = multipartuploadufile.MultipartUploadUFile(self.public_key, self.private_key, upload_suffix)

    """
        分片上传一个全新的文件
    """
    def upload_file(self, local_file_path, object_name):
        ret, resp = self.multipartuploadufile_handler.uploadfile(self.bucket, key=object_name, localfile=local_file_path)
        while True:
            if resp.status_code == 200:  # 分片上传成功
                break
            elif resp.status_code == -1:  # 网络连接问题，续传
                ret, resp = self.multipartuploadufile_handler.resumeuploadfile()
            else:  # 服务或者客户端错误
                print(resp.error)
                break
        return resp.status_code == 200

    """
        分片上传一个全新的二进制数据流
    """
    def upload_stream(self, object_name, bio, mime_type=None, header=None):
        ret, resp = self.multipartuploadufile_handler.uploadstream(self.bucket, key=object_name, stream=bio, mime_type=mime_type, header=header)
        while True:
            if resp.status_code == 200:  # 分片上传成功
                break
            elif resp.status_code == -1:  # 网络连接问题，续传
                ret, resp = self.multipartuploadufile_handler.resumeuploadstream()
            else:  # 服务器或者客户端错误
                print(resp.error)
                break
        return resp.status_code == 200

    def put_file(self, local_file_path, object_name):
        ret, resp = self.ufile_handler.putfile(self.bucket, key=object_name, localfile=local_file_path, header=None)
        print("ret:{} status_code:{} resp:{}".format(ret, resp.status_code, resp))
        return resp.status_code == 200

    def put_stream(self, object_name, bio, mime_type=None, header=None):
        ret, resp = self.ufile_handler.putstream(bucket=self.bucket, key=object_name, stream=bio, mime_type=mime_type, header=header)
        return resp.status_code == 200

    def put_list_json(self, object_name, object_list):
        raw_data = None;
        for obj in object_list:
            obj_json = json.dumps(obj, ensure_ascii=False)
            if raw_data is None:
                raw_data = obj_json
            else:
                raw_data = raw_data + "\n" + obj_json

        raw_data = raw_data.encode("utf-8")
        raw_size = len(raw_data)
        raw_data_bio = io.BytesIO(raw_data)
        self.put_stream(object_name, raw_data_bio)

    def delete_dir(self, object_name):
        ret, resp = self.ufile_handler.deletefile(bucket=self.bucket, key=object_name)
        return resp.status_code == 200

    # 因为一次查询返回数量存在最大限制，所以若一次查询无法获得所有结果，则根据返回值'NextMarker'循环遍历获得所有结果
    def loop_list(self,prefix='', marker='', maxkeys=100, delimiter=''):
        while True:
            ret, resp = self.ufile_handler.listobjects(self.bucket, prefix=prefix, maxkeys=maxkeys, marker=marker,
                                                       delimiter=delimiter)
            marker = ret['NextMarker']
            if resp.status_code == 200:
                if delimiter == "":
                    for content in ret['Contents']:  # 子文件列表
                        yield content["Key"]
                    if len(marker) <= 0 or maxkeys > len(ret['Contents']):
                        break
                if delimiter == "/":
                    for common_prefix in ret['CommonPrefixes']:  # 子目录列表
                        yield common_prefix["Prefix"]
                    if len(marker) <= 0 or maxkeys > len(ret['CommonPrefixes']):
                        break

                # if len(marker) <= 0 or maxkeys < len(ret['Contents']):
                #     break
    def download_file(self,key, localfile):
        # 从私有空间下载文件
        ret, resp = self.ufile_handler.download_file(self.bucket, key, localfile, isprivate=True)
        return resp.status_code

# if __name__ == '__main__':
#     us3_client = US3Client()
#     us3_client.download_file("pdf/2025-05-10/email_ea57f8dc-fd88-54c0-b413-e18beab349ae.pdf","email_ea57f8dc-fd88-54c0-b413-e18beab349ae.pdf")